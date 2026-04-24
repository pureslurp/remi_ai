"""Trial caps, paid-tier monthly usage, and subscription tier checks (token-metered).

Tiers (subscription_tier column):
  "free" / "trial"  — permanent free tier; lifetime token cap FREE_MAX_TOKENS
  "pro"             — $20/mo; monthly cap PRO_INCLUDED_TOKENS_PER_MONTH
  "max"             — $60/mo; monthly cap MAX_INCLUDED_TOKENS_PER_MONTH
  "ultra"           — $100/mo; monthly cap ULTRA_INCLUDED_TOKENS_PER_MONTH

"trial" is treated identically to "free" for backward compatibility with accounts
created before the Stripe billing migration.

Paid tiers (pro/max/ultra) use pro_tokens_used + pro_billing_month columns for
their rolling monthly counter.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import (
    ADMIN_EMAILS,
    FREE_MAX_TOKENS,
    LOCAL_ACCOUNT_ID,
    MAX_INCLUDED_TOKENS_PER_MONTH,
    OUTPUT_TOKEN_QUOTA_MULTIPLIER,
    PRO_INCLUDED_TOKENS_PER_MONTH,
    TRIAL_MAX_DAYS,
    TRIAL_MAX_TOKENS,
    ULTRA_INCLUDED_TOKENS_PER_MONTH,
    UPGRADE_CHECKOUT_URL,
)
from services.chat_token_estimate import raw_to_billable_units

if TYPE_CHECKING:
    from models import Account

# Valid paid tiers and their monthly token limits
_PAID_MONTHLY_LIMITS: dict[str, int] = {
    "pro": PRO_INCLUDED_TOKENS_PER_MONTH,
    "max": MAX_INCLUDED_TOKENS_PER_MONTH,
    "ultra": ULTRA_INCLUDED_TOKENS_PER_MONTH,
}

_VALID_TIERS = frozenset({"free", "trial", "pro", "max", "ultra"})


def _utcnow() -> datetime:
    return datetime.utcnow()


def subscription_tier(account: "Account") -> str:
    """Canonical tier string. 'trial' is normalised to 'free' for all callers."""
    raw = (getattr(account, "subscription_tier", None) or "free").strip().lower()
    if raw not in _VALID_TIERS:
        return "free"
    return "free" if raw == "trial" else raw


def is_paid_tier(tier: str) -> bool:
    return tier in _PAID_MONTHLY_LIMITS


def monthly_limit_for_tier(tier: str) -> int:
    return _PAID_MONTHLY_LIMITS.get(tier, 0)


def _effective_paid_tokens_this_month(account: "Account") -> tuple[int, str | None]:
    """Read-only: if billing month rolled over, treat usage as 0 until chat commits rollover."""
    cur = _utcnow().strftime("%Y-%m")
    pm = getattr(account, "pro_billing_month", None)
    used = int(getattr(account, "pro_tokens_used", 0) or 0)
    if pm != cur:
        return 0, cur
    return used, pm


def _trial_period_expired(account: "Account") -> bool:
    """Legacy: only relevant for old 'trial' accounts that had a time cap."""
    started = getattr(account, "trial_started_at", None)
    if started is None:
        return False
    return _utcnow() - started > timedelta(days=TRIAL_MAX_DAYS)


def entitlements_payload(account: "Account") -> dict:
    """Public fields for GET /api/account/entitlements."""
    admin = is_admin(account)
    tier = subscription_tier(account)
    trial_started = getattr(account, "trial_started_at", None)
    free_used = int(getattr(account, "trial_tokens_used", 0) or 0)
    paid_used_display, paid_month_display = _effective_paid_tokens_this_month(account)

    monthly_limit = monthly_limit_for_tier(tier)

    # Free-tier time-window logic (legacy; new "free" accounts have no time limit)
    trial_ends_at: str | None = None
    if tier == "free" and trial_started:
        ends = trial_started + timedelta(days=TRIAL_MAX_DAYS)
        trial_ends_at = ends.isoformat() + "Z"

    if is_paid_tier(tier):
        paid_remaining = max(0, monthly_limit - paid_used_display)
        subscription_status = getattr(account, "subscription_status", None)
        # Treat past_due as still allowed (grace period); canceled/null = not paid
        can_send = paid_remaining > 0 and subscription_status in ("active", "past_due", "trialing")
    else:
        free_remaining = max(0, FREE_MAX_TOKENS - free_used)
        expired = _trial_period_expired(account)
        can_send = not expired and free_remaining > 0
        paid_remaining = 0
        paid_month_display = None

    if admin:
        can_send = True

    return {
        "is_admin": admin,
        "subscription_tier": tier,
        # Free / trial fields (always present for backward compat)
        "trial_max_tokens": TRIAL_MAX_TOKENS,
        "trial_tokens_used": free_used,
        "trial_tokens_remaining": max(0, FREE_MAX_TOKENS - free_used) if not is_paid_tier(tier) else 0,
        "trial_max_days": TRIAL_MAX_DAYS,
        "trial_started_at": trial_started.isoformat() + "Z" if trial_started else None,
        "trial_ends_at": trial_ends_at,
        # Paid tier fields
        "pro_included_tokens_per_month": monthly_limit if is_paid_tier(tier) else PRO_INCLUDED_TOKENS_PER_MONTH,
        "pro_tokens_used": paid_used_display if is_paid_tier(tier) else 0,
        "pro_tokens_remaining": paid_remaining if is_paid_tier(tier) else 0,
        "pro_billing_month": paid_month_display if is_paid_tier(tier) else None,
        "can_send_chat": can_send,
        "upgrade_url": UPGRADE_CHECKOUT_URL,
        "quota_output_multiplier": OUTPUT_TOKEN_QUOTA_MULTIPLIER,
        # Stripe subscription info for frontend
        "subscription_status": getattr(account, "subscription_status", None),
        "subscription_current_period_end": (
            getattr(account, "subscription_current_period_end", None).isoformat() + "Z"
            if getattr(account, "subscription_current_period_end", None)
            else None
        ),
    }


def _ensure_paid_month(account: "Account") -> None:
    """Reset paid-tier counter when calendar month changes."""
    cur = _utcnow().strftime("%Y-%m")
    pm = getattr(account, "pro_billing_month", None)
    if pm != cur:
        account.pro_billing_month = cur
        account.pro_tokens_used = 0


def is_admin(account: "Account") -> bool:
    email = (getattr(account, "email", None) or "").strip().lower()
    return bool(email and email in ADMIN_EMAILS)


def assert_chat_allowed(account: "Account", db: Session, estimated_additional_tokens: int) -> None:
    """
    Raises HTTPException if this request would exceed the account budget (pre-flight).
    `estimated_additional_tokens` is **billable units** (input + weighted output budget).
    Mutates account (trial start, paid month rollover) — caller must commit.
    """
    if is_admin(account):
        return

    est = max(0, int(estimated_additional_tokens))
    tier = subscription_tier(account)

    if is_paid_tier(tier):
        subscription_status = getattr(account, "subscription_status", None)
        if subscription_status not in ("active", "past_due", "trialing"):
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "subscription_inactive",
                    "message": "Your subscription is no longer active.",
                    "instruction": "Please update your billing details to continue using Reco.",
                    "upgrade_url": UPGRADE_CHECKOUT_URL,
                },
            )
        _ensure_paid_month(account)
        monthly_limit = monthly_limit_for_tier(tier)
        used = int(getattr(account, "pro_tokens_used", 0) or 0)
        if used >= monthly_limit:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "quota_exceeded",
                    "message": f"You've used all {monthly_limit:,} included billable units for this month.",
                    "instruction": "Upgrade to a higher plan or wait until your monthly allowance resets.",
                    "upgrade_url": UPGRADE_CHECKOUT_URL,
                },
            )
        if used + est > monthly_limit:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "quota_exceeded",
                    "message": "This prompt is too large for your remaining monthly usage allowance.",
                    "instruction": "Try a shorter question, remove some context, or upgrade for more tokens.",
                    "upgrade_url": UPGRADE_CHECKOUT_URL,
                },
            )
        return

    # Free / trial tier — lifetime token cap
    used = int(getattr(account, "trial_tokens_used", 0) or 0)
    if used >= FREE_MAX_TOKENS:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "free_quota_exhausted",
                "message": f"You've used all {FREE_MAX_TOKENS:,} free billable units.",
                "instruction": "Upgrade to Pro, Max, or Ultra for a monthly token allowance.",
                "upgrade_url": UPGRADE_CHECKOUT_URL,
            },
        )
    if used + est > FREE_MAX_TOKENS:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "free_quota_exhausted",
                "message": "This prompt is too large for your remaining free usage.",
                "instruction": "Try a shorter question or upgrade for more tokens.",
                "upgrade_url": UPGRADE_CHECKOUT_URL,
            },
        )


def increment_usage_after_chat_completion(
    account: "Account",
    db: Session,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Call after a chat completion with provider-reported (or fallback) raw token counts."""
    total = raw_to_billable_units(input_tokens, output_tokens)
    if total <= 0:
        return
    tier = subscription_tier(account)
    if is_paid_tier(tier):
        _ensure_paid_month(account)
        account.pro_tokens_used = int(getattr(account, "pro_tokens_used", 0) or 0) + total
    else:
        account.trial_tokens_used = int(getattr(account, "trial_tokens_used", 0) or 0) + total
    db.add(account)


def default_subscription_tier_for_new_account(account_id: str) -> str:
    """SQLite local dev account is Pro; everyone else starts on free tier."""
    return "pro" if account_id == LOCAL_ACCOUNT_ID else "free"
