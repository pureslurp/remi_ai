"""Trial caps, Pro monthly usage, and subscription tier checks (token-metered).

Per-user / BYOK API keys are out of scope (fully managed host keys only).
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.orm import Session

from config import (
    ADMIN_EMAILS,
    LOCAL_ACCOUNT_ID,
    OUTPUT_TOKEN_QUOTA_MULTIPLIER,
    PRO_INCLUDED_TOKENS_PER_MONTH,
    TRIAL_MAX_TOKENS,
    UPGRADE_CHECKOUT_URL,
)
from services.chat_token_estimate import raw_to_billable_units

if TYPE_CHECKING:
    from models import Account


def _utcnow() -> datetime:
    return datetime.utcnow()


def _effective_pro_tokens_this_month(account: Account) -> tuple[int, str | None]:
    """Read-only: if billing month rolled over, treat usage as 0 until chat commits rollover."""
    cur = _utcnow().strftime("%Y-%m")
    pm = getattr(account, "pro_billing_month", None)
    used = int(getattr(account, "pro_tokens_used", 0) or 0)
    if pm != cur:
        return 0, cur
    return used, pm


def _trial_period_expired(account: Account) -> bool:
    started = getattr(account, "trial_started_at", None)
    if started is None:
        return False
    return _utcnow() - started > timedelta(days=TRIAL_MAX_DAYS)


def subscription_tier(account: Account) -> str:
    t = (getattr(account, "subscription_tier", None) or "trial").strip().lower()
    return t if t in ("trial", "pro") else "trial"


def entitlements_payload(account: Account) -> dict:
    """Public fields for GET /api/account/entitlements."""
    tier = subscription_tier(account)
    trial_started = getattr(account, "trial_started_at", None)
    trial_used = int(getattr(account, "trial_tokens_used", 0) or 0)
    pro_used_display, pro_month_display = _effective_pro_tokens_this_month(account)

    trial_ends_at: str | None = None
    if tier == "trial" and trial_started:
        ends = trial_started + timedelta(days=TRIAL_MAX_DAYS)
        trial_ends_at = ends.isoformat() + "Z"

    trial_remaining = max(0, TRIAL_MAX_TOKENS - trial_used)
    pro_remaining = max(0, PRO_INCLUDED_TOKENS_PER_MONTH - pro_used_display)

    if tier == "pro":
        can_send = pro_remaining > 0
    else:
        expired = _trial_period_expired(account)
        exhausted = trial_used >= TRIAL_MAX_TOKENS
        can_send = not expired and not exhausted

    return {
        "subscription_tier": tier,
        "trial_max_tokens": TRIAL_MAX_TOKENS,
        "trial_tokens_used": trial_used,
        "trial_tokens_remaining": trial_remaining,
        "trial_max_days": TRIAL_MAX_DAYS,
        "trial_started_at": trial_started.isoformat() + "Z" if trial_started else None,
        "trial_ends_at": trial_ends_at,
        "pro_included_tokens_per_month": PRO_INCLUDED_TOKENS_PER_MONTH,
        "pro_tokens_used": pro_used_display if tier == "pro" else 0,
        "pro_tokens_remaining": pro_remaining if tier == "pro" else 0,
        "pro_billing_month": pro_month_display,
        "can_send_chat": can_send,
        "upgrade_url": UPGRADE_CHECKOUT_URL,
        "quota_output_multiplier": OUTPUT_TOKEN_QUOTA_MULTIPLIER,
    }


def _ensure_pro_month(account: Account) -> None:
    """Reset Pro counter when calendar month changes."""
    cur = _utcnow().strftime("%Y-%m")
    pm = getattr(account, "pro_billing_month", None)
    if pm != cur:
        account.pro_billing_month = cur
        account.pro_tokens_used = 0


def is_admin(account: Account) -> bool:
    email = (getattr(account, "email", None) or "").strip().lower()
    return bool(email and email in ADMIN_EMAILS)


def assert_chat_allowed(account: Account, db: Session, estimated_additional_tokens: int) -> None:
    """
    Raises HTTPException if this request would exceed the account budget (pre-flight).
    `estimated_additional_tokens` is **billable units** (input + weighted output budget).
    Mutates account (trial start, pro month rollover) — caller must commit.
    """
    if is_admin(account):
        return

    est = max(0, int(estimated_additional_tokens))
    tier = subscription_tier(account)

    if tier == "pro":
        _ensure_pro_month(account)
        used = int(getattr(account, "pro_tokens_used", 0) or 0)
        if used >= PRO_INCLUDED_TOKENS_PER_MONTH:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "pro_quota_exceeded",
                    "message": f"You've used all {PRO_INCLUDED_TOKENS_PER_MONTH:,} included billable units for this month.",
                    "instruction": "Upgrade to a higher plan, buy add-on usage when available, or wait until your monthly allowance resets.",
                    "upgrade_url": UPGRADE_CHECKOUT_URL,
                },
            )
        if used + est > PRO_INCLUDED_TOKENS_PER_MONTH:
            raise HTTPException(
                status_code=402,
                detail={
                    "code": "pro_quota_exceeded",
                    "message": "This prompt is too large for your remaining monthly usage allowance.",
                    "instruction": "Try a shorter question, remove some context, or upgrade for more tokens.",
                    "upgrade_url": UPGRADE_CHECKOUT_URL,
                },
            )
        return

    # free tier — token cap only, no time limit
    used = int(getattr(account, "trial_tokens_used", 0) or 0)
    if used >= TRIAL_MAX_TOKENS:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_tokens_exhausted",
                "message": f"You've used all {TRIAL_MAX_TOKENS:,} trial billable units.",
                "instruction": "Upgrade to Pro for a higher monthly allowance, or buy add-on usage when we offer it.",
                "upgrade_url": UPGRADE_CHECKOUT_URL,
            },
        )
    if used + est > TRIAL_MAX_TOKENS:
        raise HTTPException(
            status_code=402,
            detail={
                "code": "trial_tokens_exhausted",
                "message": "This prompt is too large for your remaining trial usage allowance.",
                "instruction": "Try a shorter question or upgrade to Pro for more tokens.",
                "upgrade_url": UPGRADE_CHECKOUT_URL,
            },
        )


def increment_usage_after_chat_completion(
    account: Account,
    db: Session,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """Call after a chat completion with provider-reported (or fallback) raw token counts."""
    total = raw_to_billable_units(input_tokens, output_tokens)
    if total <= 0:
        return
    tier = subscription_tier(account)
    if tier == "pro":
        _ensure_pro_month(account)
        account.pro_tokens_used = int(getattr(account, "pro_tokens_used", 0) or 0) + total
    else:
        account.trial_tokens_used = int(getattr(account, "trial_tokens_used", 0) or 0) + total
    db.add(account)


def default_subscription_tier_for_new_account(account_id: str) -> str:
    """SQLite local dev account is Pro; everyone else starts on trial."""
    return "pro" if account_id == LOCAL_ACCOUNT_ID else "trial"
