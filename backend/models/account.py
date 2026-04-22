from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class Account(Base):
    """User account — created via Google OAuth (`sub` as id) or email signup (UUID as id)."""

    __tablename__ = "accounts"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True)
    name = Column(String)
    picture = Column(String)
    auth_provider = Column(String, nullable=False, default="google")  # "google" | "email"
    password_hash = Column(String, nullable=True)  # null for Google-only accounts
    # Optional overrides for role-specific AI strategy text (NULL = use app default).
    system_prompt_buyer = Column(Text, nullable=True)
    system_prompt_seller = Column(Text, nullable=True)
    system_prompt_buyer_seller = Column(Text, nullable=True)
    # Billing: free | trial | pro | max | ultra (managed keys; usage in trial_tokens_used / pro_tokens_used)
    # "trial" is treated identically to "free" for backward compatibility.
    subscription_tier = Column(String, nullable=False, default="free")
    trial_started_at = Column(DateTime, nullable=True)
    trial_messages_used = Column(Integer, nullable=False, default=0)  # legacy; not used for enforcement
    trial_tokens_used = Column(Integer, nullable=False, default=0)
    pro_billing_month = Column(String, nullable=True)  # "YYYY-MM" for rolling monthly counter
    pro_messages_used = Column(Integer, nullable=False, default=0)  # legacy
    pro_tokens_used = Column(Integer, nullable=False, default=0)
    # Stripe subscription tracking
    stripe_customer_id = Column(String, nullable=True)
    stripe_subscription_id = Column(String, nullable=True)
    subscription_status = Column(String, nullable=True)  # "active" | "past_due" | "canceled" | null
    subscription_current_period_end = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
