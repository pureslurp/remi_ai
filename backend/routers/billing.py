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

    try:
        session = sc.checkout.sessions.create(**session_params)
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
        session = sc.billing_portal.sessions.create(
            customer=customer_id,
            return_url=FRONTEND_ORIGIN,
        )
    except stripe.StripeError as e:
        logger.error("Stripe portal error: %s", e)
        raise HTTPException(status_code=502, detail=f"Stripe error: {e.user_message or str(e)}")

    return {"url": session.url}


# ---------------------------------------------------------------------------
# POST /api/billing/webhook  (no auth — validated by Stripe signature)
# ---------------------------------------------------------------------------

@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
    db: Session = Depends(get_db),
):
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
    data = event["data"]["object"]

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

    return {"received": True}


# ---------------------------------------------------------------------------
# Webhook handlers (each commits on success)
# ---------------------------------------------------------------------------

def _find_account_by_customer(customer_id: str, db: Session) -> Account | None:
    return db.query(Account).filter(Account.stripe_customer_id == customer_id).first()


def _handle_checkout_completed(session: dict, db: Session) -> None:
    account_id: str | None = session.get("client_reference_id")
    customer_id: str | None = session.get("customer")
    subscription_id: str | None = session.get("subscription")
    plan: str = (session.get("metadata") or {}).get("plan", "pro")

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
    # Reset the monthly usage counter for the new billing period
    acc.pro_billing_month = datetime.utcnow().strftime("%Y-%m")
    acc.pro_tokens_used = 0
    db.commit()
    logger.info("Activated %s plan for account %s (sub=%s)", plan, account_id, subscription_id)


def _handle_subscription_updated(sub: dict, db: Session) -> None:
    customer_id: str | None = sub.get("customer")
    if not customer_id:
        return

    acc = _find_account_by_customer(customer_id, db)
    if not acc:
        logger.warning("subscription.updated: no account found for customer %s", customer_id)
        return

    # Determine tier from price ID
    items = (sub.get("items") or {}).get("data") or []
    price_id: str | None = items[0]["price"]["id"] if items else None
    new_tier = _PRICE_TO_PLAN.get(price_id, acc.subscription_tier) if price_id else acc.subscription_tier

    new_status: str = sub.get("status", "active")
    period_end_ts = sub.get("current_period_end")
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
    db.commit()
    logger.info("Subscription updated for customer %s: tier=%s status=%s", customer_id, new_tier, new_status)


def _handle_subscription_deleted(sub: dict, db: Session) -> None:
    customer_id: str | None = sub.get("customer")
    if not customer_id:
        return

    acc = _find_account_by_customer(customer_id, db)
    if not acc:
        return

    acc.subscription_tier = "free"
    acc.subscription_status = "canceled"
    acc.stripe_subscription_id = None
    db.commit()
    logger.info("Subscription canceled for customer %s — downgraded to free", customer_id)


def _handle_payment_failed(invoice: dict, db: Session) -> None:
    customer_id: str | None = invoice.get("customer")
    if not customer_id:
        return

    acc = _find_account_by_customer(customer_id, db)
    if not acc:
        return

    acc.subscription_status = "past_due"
    db.commit()
    logger.info("Payment failed for customer %s — marked past_due", customer_id)
