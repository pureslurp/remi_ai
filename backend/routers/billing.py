"""Stripe billing: checkout sessions, customer portal, and webhook handler."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

import stripe
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import (
    FRONTEND_ORIGIN,
    STRIPE_PRICE_MAX,
    STRIPE_PRICE_PRO,
    STRIPE_PRICE_ULTRA,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from database import get_db
from deps.auth import CurrentAccount
from models import Account

logger = logging.getLogger("reco.billing")

router = APIRouter(prefix="/api/billing", tags=["billing"])


def _stripe_expandable_id(value: object) -> str | None:
    """Normalize Stripe id fields: string id, or expanded object with ``id``."""
    if value is None:
        return None
    if isinstance(value, str) and value:
        return value
    if isinstance(value, dict) and value.get("id") is not None:
        return str(value["id"])
    return str(value) if value else None


def _line_item_price_id(item: object) -> str | None:
    """Handle ``price`` as id string (newer API) or ``{\"id\": ...}`` object."""
    if not isinstance(item, dict):
        return None
    p = item.get("price")
    if p is None:
        return None
    if isinstance(p, str) and p:
        return p
    if isinstance(p, dict) and p.get("id") is not None:
        return str(p["id"])
    return None


def _first_subscription_price_id(sub: dict) -> str | None:
    items = (sub.get("items") or {}) if isinstance(sub.get("items"), dict) else {}
    data = items.get("data") or []
    if not data or not isinstance(data, list):
        return None
    return _line_item_price_id(data[0]) if data else None


def _metadata_plan(metadata: object) -> str:
    if not isinstance(metadata, dict):
        return "pro"
    p = metadata.get("plan")
    if p is None or p == "":
        return "pro"
    return str(p)

# Map plan names → Stripe Price IDs (set in config / env)
_PLAN_TO_PRICE: dict[str, str | None] = {
    "pro": STRIPE_PRICE_PRO,
    "max": STRIPE_PRICE_MAX,
    "ultra": STRIPE_PRICE_ULTRA,
}

# Map Stripe Price IDs → tier names (built at import from the same config values)
_PRICE_TO_PLAN: dict[str, str] = {}
for _plan, _price in _PLAN_TO_PRICE.items():
    if _price:
        _PRICE_TO_PLAN[_price] = _plan

_PAID_TIER_RANK: dict[str, int] = {"pro": 1, "max": 2, "ultra": 3}


def _stripe_subscription_to_dict(sub: object) -> dict:
    if hasattr(sub, "to_dict"):
        raw = sub.to_dict()
        return raw if isinstance(raw, dict) else {}
    return sub if isinstance(sub, dict) else {}


def _clear_scheduled_downgrade(acc: Account) -> None:
    acc.subscription_scheduled_plan = None
    acc.subscription_schedule_id = None


def _try_release_subscription_schedule(
    sc: stripe.StripeClient, schedule_id: str | None, *, strict: bool = False
) -> None:
    """Detach a subscription schedule; subscription keeps current price until period end."""
    if not schedule_id:
        return
    try:
        sc.v1.subscription_schedules.release(schedule_id)
    except stripe.StripeError as e:
        logger.warning("Could not release subscription schedule %s: %s", schedule_id, e)
        if strict:
            raise


def _stripe_client() -> stripe.StripeClient:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=503, detail="Stripe is not configured on this server.")
    return stripe.StripeClient(STRIPE_SECRET_KEY)


# ---------------------------------------------------------------------------
# POST /api/billing/create-checkout-session
# ---------------------------------------------------------------------------

class CheckoutRequest(BaseModel):
    plan: Literal["pro", "max", "ultra"]


@router.post("/create-checkout-session")
def create_checkout_session(
    body: CheckoutRequest,
    account_id: CurrentAccount,
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for a paid plan upgrade."""
    price_id = _PLAN_TO_PRICE.get(body.plan)
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Stripe price for plan '{body.plan}' is not configured. Set STRIPE_PRICE_{body.plan.upper()} in environment.",
        )

    sc = _stripe_client()
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    # Re-use existing Stripe customer if we have one
    customer_id: str | None = getattr(acc, "stripe_customer_id", None)

    session_params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": f"{FRONTEND_ORIGIN}?checkout_success=1",
        "cancel_url": f"{FRONTEND_ORIGIN}?checkout_canceled=1",
        "client_reference_id": account_id,
        "metadata": {"plan": body.plan, "account_id": account_id},
        "allow_promotion_codes": True,
    }
    if customer_id:
        session_params["customer"] = customer_id
    else:
        session_params["customer_email"] = acc.email or None

    # StripeClient (stripe-python v10+) takes a single `params` dict, not **kwargs
    try:
        session = sc.v1.checkout.sessions.create(params=session_params)
    except stripe.StripeError as e:
        logger.error("Stripe checkout error: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# POST /api/billing/portal
# ---------------------------------------------------------------------------

@router.post("/portal")
def create_portal_session(
    account_id: CurrentAccount,
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session for subscription management."""
    sc = _stripe_client()
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    customer_id: str | None = getattr(acc, "stripe_customer_id", None)
    if not customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    try:
        session = sc.v1.billing_portal.sessions.create(
            params={"customer": customer_id, "return_url": FRONTEND_ORIGIN},
        )
    except stripe.StripeError as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# POST /api/billing/change-plan
# ---------------------------------------------------------------------------

class ChangePlanRequest(BaseModel):
    plan: Literal["pro", "max", "ultra"]


@router.post("/change-plan")
def change_plan(
    body: ChangePlanRequest,
    account_id: CurrentAccount,
    db: Session = Depends(get_db),
):
    """Upgrade immediately (prorated charge) or queue a downgrade for the next billing period (no credit)."""
    price_id = _PLAN_TO_PRICE.get(body.plan)
    if not price_id:
        raise HTTPException(
            status_code=503,
            detail=f"Stripe price for plan '{body.plan}' is not configured.",
        )

    sc = _stripe_client()
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    sub_id: str | None = getattr(acc, "stripe_subscription_id", None)
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription found.")

    if bool(getattr(acc, "subscription_cancel_at_period_end", False)):
        raise HTTPException(
            status_code=400,
            detail="Subscription is set to cancel at period end. Reactivate it first to change plans.",
        )

    try:
        sub = sc.v1.subscriptions.retrieve(sub_id)
        sub_d = _stripe_subscription_to_dict(sub)
        items_data = sub_d.get("items", {}).get("data", []) if isinstance(sub_d.get("items"), dict) else []
        if not items_data:
            raise HTTPException(status_code=400, detail="Could not retrieve subscription items.")
        item_id = items_data[0]["id"]

        cur_price_id = _first_subscription_price_id(sub_d)
        current_plan = (
            (_PRICE_TO_PLAN.get(cur_price_id) if cur_price_id else None)
            or (getattr(acc, "subscription_tier", None) or "")
        ).lower()
        if current_plan not in _PAID_TIER_RANK:
            raise HTTPException(status_code=400, detail="Could not determine current subscription plan.")

        cur_rank = _PAID_TIER_RANK[current_plan]
        tgt_rank = _PAID_TIER_RANK[body.plan]

        if tgt_rank == cur_rank:
            return {"ok": True, "scheduled": False}

        # Upgrade: apply immediately with proration; drop any pending downgrade schedule first.
        if tgt_rank > cur_rank:
            _try_release_subscription_schedule(sc, getattr(acc, "subscription_schedule_id", None))
            _clear_scheduled_downgrade(acc)
            sc.v1.subscriptions.update(
                sub_id,
                params={
                    "items": [{"id": item_id, "price": price_id}],
                    "proration_behavior": "create_prorations",
                },
            )
            db.commit()
            return {"ok": True, "scheduled": False}

        # Downgrade: subscription schedule, change at period end, no proration credit.
        if getattr(acc, "subscription_scheduled_plan", None) == body.plan and getattr(
            acc, "subscription_schedule_id", None
        ):
            pe = sub_d.get("current_period_end")
            if pe is None and items_data:
                pe = items_data[0].get("current_period_end")
            effective_at = (
                datetime.utcfromtimestamp(int(pe)).isoformat() + "Z" if pe is not None else None
            )
            return {
                "ok": True,
                "scheduled": True,
                "scheduled_plan": body.plan,
                "effective_at": effective_at,
            }

        _try_release_subscription_schedule(sc, getattr(acc, "subscription_schedule_id", None))
        _clear_scheduled_downgrade(acc)

        sched_created: object | None = None
        try:
            sched_created = sc.v1.subscription_schedules.create(params={"from_subscription": sub_id})
            sched_d = sched_created.to_dict() if hasattr(sched_created, "to_dict") else {}
            phases = sched_d.get("phases") or []
            if not phases or not isinstance(phases[0], dict):
                raise HTTPException(status_code=400, detail="Could not read subscription schedule phase.")

            ph0 = phases[0]
            p0_item = (ph0.get("items") or [{}])[0]
            p0_price = p0_item.get("price")
            if isinstance(p0_price, dict):
                p0_price = p0_price.get("id")
            qty = int(p0_item.get("quantity") or 1)
            phase0: dict = {
                "items": [{"price": p0_price, "quantity": qty}],
                "start_date": ph0["start_date"],
                "end_date": ph0["end_date"],
                "proration_behavior": "none",
            }
            phase1: dict = {
                "items": [{"price": price_id, "quantity": 1}],
                "proration_behavior": "none",
                "duration": {"interval": "month", "interval_count": 1},
            }
            sched_id_str = str(sched_d.get("id", ""))
            updated = sc.v1.subscription_schedules.update(
                sched_id_str,
                params={
                    "phases": [phase0, phase1],
                    "end_behavior": "release",
                    "proration_behavior": "none",
                },
            )
            updated_d = updated.to_dict() if hasattr(updated, "to_dict") else {}
            acc.subscription_scheduled_plan = body.plan
            acc.subscription_schedule_id = str(updated_d.get("id", sched_id_str))
            db.commit()

            eff_ts = ph0.get("end_date")
            effective_at = datetime.utcfromtimestamp(int(eff_ts)).isoformat() + "Z" if eff_ts is not None else None
            return {
                "ok": True,
                "scheduled": True,
                "scheduled_plan": body.plan,
                "effective_at": effective_at,
            }
        except (stripe.StripeError, HTTPException):
            if sched_created is not None and hasattr(sched_created, "id"):
                try:
                    sc.v1.subscription_schedules.release(str(sched_created.id))
                except stripe.StripeError:
                    pass
            raise
    except stripe.StripeError as e:
        logger.error("Stripe change-plan error: %s", e)
        db.rollback()
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}")


# ---------------------------------------------------------------------------
# POST /api/billing/cancel-scheduled-downgrade
# ---------------------------------------------------------------------------


@router.post("/cancel-scheduled-downgrade")
def cancel_scheduled_downgrade(
    account_id: CurrentAccount,
    db: Session = Depends(get_db),
):
    """Undo a pending end-of-period downgrade (releases the Stripe subscription schedule)."""
    sc = _stripe_client()
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    sched_id: str | None = getattr(acc, "subscription_schedule_id", None)
    if not sched_id:
        raise HTTPException(status_code=400, detail="No scheduled plan change to cancel.")

    try:
        _try_release_subscription_schedule(sc, sched_id, strict=True)
    except stripe.StripeError as e:
        logger.error("Stripe cancel-scheduled-downgrade error: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}") from e

    _clear_scheduled_downgrade(acc)
    db.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/billing/cancel
# ---------------------------------------------------------------------------

@router.post("/cancel")
def cancel_subscription(
    account_id: CurrentAccount,
    db: Session = Depends(get_db),
):
    """Cancel subscription at end of current billing period (no immediate loss of access)."""
    sc = _stripe_client()
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    sub_id: str | None = getattr(acc, "stripe_subscription_id", None)
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription found.")

    try:
        _try_release_subscription_schedule(sc, getattr(acc, "subscription_schedule_id", None))
        _clear_scheduled_downgrade(acc)
        sc.v1.subscriptions.update(sub_id, params={"cancel_at_period_end": True})
    except stripe.StripeError as e:
        logger.error("Stripe cancel error: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}")

    db.commit()

    period_end = getattr(acc, "subscription_current_period_end", None)
    access_until = (period_end.isoformat() + "Z") if period_end else None
    return {"ok": True, "access_until": access_until}


# ---------------------------------------------------------------------------
# POST /api/billing/reactivate
# ---------------------------------------------------------------------------

@router.post("/reactivate")
def reactivate_subscription(
    account_id: CurrentAccount,
    db: Session = Depends(get_db),
):
    """Undo a pending cancellation (cancel_at_period_end → False)."""
    sc = _stripe_client()
    acc = db.get(Account, account_id)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    sub_id: str | None = getattr(acc, "stripe_subscription_id", None)
    if not sub_id:
        raise HTTPException(status_code=400, detail="No active subscription found.")

    try:
        sc.v1.subscriptions.update(sub_id, params={"cancel_at_period_end": False})
    except stripe.StripeError as e:
        logger.error("Stripe reactivate error: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"ok": True}


# ---------------------------------------------------------------------------
# POST /api/billing/webhook  (no auth — validated by Stripe signature)
# ---------------------------------------------------------------------------

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
    """Must read the raw request body before signature verification.

    Using a typed parameter (bytes/dict/Pydantic) makes FastAPI parse/validate the JSON
    before we can verify Stripe's signature on the exact bytes Stripe sent.
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Webhook secret not configured.")

    payload = await request.body()
    try:
        event = stripe.Webhook.construct_event(payload, stripe_signature, STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload.")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature.")

    etype = event["type"]
    raw_obj = event["data"]["object"]
    # stripe-python returns a StripeObject, which doesn't implement `.get()`.
    # Convert to a plain (recursively nested) dict so our handlers can use dict APIs.
    if hasattr(raw_obj, "to_dict"):
        data = raw_obj.to_dict()
    elif isinstance(raw_obj, dict):
        data = dict(raw_obj)
    else:
        data = raw_obj

    try:
        if etype == "checkout.session.completed":
            _handle_checkout_completed(data, db)
        elif etype == "customer.subscription.updated":
            _handle_subscription_updated(data, db)
        elif etype == "customer.subscription.deleted":
            _handle_subscription_deleted(data, db)
        elif etype == "invoice.payment_failed":
            _handle_payment_failed(data, db)
        else:
            logger.debug("Unhandled Stripe event: %s", etype)
    except Exception:
        logger.exception("Stripe webhook failed (type=%s)", etype)
        raise HTTPException(status_code=500, detail="webhook handler failed") from None

    return {"received": True}


# ---------------------------------------------------------------------------
# Webhook handlers (each commits on success)
# ---------------------------------------------------------------------------

def _find_account_by_customer(customer_id: str, db: Session) -> Account | None:
    return db.query(Account).filter(Account.stripe_customer_id == customer_id).first()


def _current_period_end_unix_from_subscription_dict(raw: dict) -> int | None:
    """Newer Stripe API versions put ``current_period_end`` on each line item, not the subscription root."""
    ts = raw.get("current_period_end")
    if ts is not None:
        return int(ts)
    items = raw.get("items")
    if not isinstance(items, dict):
        return None
    data = items.get("data") or []
    if not data or not isinstance(data, list) or not isinstance(data[0], dict):
        return None
    line_ts = data[0].get("current_period_end")
    return int(line_ts) if line_ts is not None else None


def _fetch_subscription_current_period_end(subscription_id: str | None) -> datetime | None:
    """Stripe checkout.session does not include subscription period; retrieve the Subscription."""
    if not subscription_id or not STRIPE_SECRET_KEY:
        return None
    sc = stripe.StripeClient(STRIPE_SECRET_KEY)
    try:
        sub = sc.v1.subscriptions.retrieve(subscription_id)
    except stripe.StripeError as e:
        logger.warning("Could not retrieve subscription %s for current_period_end: %s", subscription_id, e)
        return None
    raw = sub.to_dict() if hasattr(sub, "to_dict") else sub
    if not isinstance(raw, dict):
        return None
    try:
        ts = _current_period_end_unix_from_subscription_dict(raw)
    except (TypeError, ValueError):
        return None
    if ts is None:
        return None
    try:
        return datetime.utcfromtimestamp(int(ts))
    except (TypeError, ValueError, OSError):
        return None


def _handle_checkout_completed(session: dict, db: Session) -> None:
    account_id: str | None = session.get("client_reference_id")
    customer_id = _stripe_expandable_id(session.get("customer"))
    subscription_id = _stripe_expandable_id(session.get("subscription"))
    plan: str = _metadata_plan(session.get("metadata"))

    if not account_id:
        logger.warning("checkout.session.completed missing client_reference_id")
        return

    acc = db.get(Account, account_id)
    if not acc:
        logger.warning("checkout.session.completed: account %s not found", account_id)
        return

    acc.stripe_customer_id = customer_id
    acc.stripe_subscription_id = subscription_id
    acc.subscription_tier = plan
    acc.subscription_status = "active"
    _clear_scheduled_downgrade(acc)
    period_end = _fetch_subscription_current_period_end(subscription_id)
    if period_end:
        acc.subscription_current_period_end = period_end
    # Reset the monthly usage counter for the new billing period
    acc.pro_billing_month = datetime.utcnow().strftime("%Y-%m")
    acc.pro_tokens_used = 0
    db.commit()
    logger.info(
        "Activated %s plan for account %s (sub=%s period_end=%s)",
        plan,
        account_id,
        subscription_id,
        acc.subscription_current_period_end,
    )


def _handle_subscription_updated(sub: dict, db: Session) -> None:
    customer_id = _stripe_expandable_id(sub.get("customer"))
    if not customer_id:
        return

    acc = _find_account_by_customer(customer_id, db)
    if not acc:
        logger.warning("subscription.updated: no account found for customer %s", customer_id)
        return

    price_id = _first_subscription_price_id(sub)
    new_tier = _PRICE_TO_PLAN.get(price_id, acc.subscription_tier) if price_id else acc.subscription_tier

    new_status: str = sub.get("status", "active")
    try:
        period_end_ts = _current_period_end_unix_from_subscription_dict(sub)
    except (TypeError, ValueError):
        period_end_ts = None
    period_end = datetime.utcfromtimestamp(period_end_ts) if period_end_ts else None

    # If plan changed, reset usage counter for the new period
    if new_tier != acc.subscription_tier:
        acc.pro_billing_month = datetime.utcnow().strftime("%Y-%m")
        acc.pro_tokens_used = 0

    acc.subscription_tier = new_tier
    acc.subscription_status = new_status
    acc.stripe_subscription_id = sub.get("id", acc.stripe_subscription_id)
    if period_end:
        acc.subscription_current_period_end = period_end
    acc.subscription_cancel_at_period_end = bool(sub.get("cancel_at_period_end", False))
    scheduled = getattr(acc, "subscription_scheduled_plan", None)
    if scheduled and new_tier == scheduled:
        _clear_scheduled_downgrade(acc)
    db.commit()
    logger.info("Subscription updated for customer %s: tier=%s status=%s cancel_at_period_end=%s", customer_id, new_tier, new_status, acc.subscription_cancel_at_period_end)


def _handle_subscription_deleted(sub: dict, db: Session) -> None:
    customer_id = _stripe_expandable_id(sub.get("customer"))
    if not customer_id:
        return

    acc = _find_account_by_customer(customer_id, db)
    if not acc:
        return

    acc.subscription_tier = "free"
    acc.subscription_status = "canceled"
    acc.stripe_subscription_id = None
    acc.subscription_cancel_at_period_end = False
    _clear_scheduled_downgrade(acc)
    db.commit()
    logger.info("Subscription canceled for customer %s — downgraded to free", customer_id)


def _handle_payment_failed(invoice: dict, db: Session) -> None:
    customer_id = _stripe_expandable_id(invoice.get("customer"))
    if not customer_id:
        return

    acc = _find_account_by_customer(customer_id, db)
    if not acc:
        return

    acc.subscription_status = "past_due"
    db.commit()
    logger.info("Payment failed for customer %s — marked past_due", customer_id)
