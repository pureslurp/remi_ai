from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from database import Base


class Account(Base):
    """Google user (OIDC `sub`) — one row per person using the app."""

    __tablename__ = "accounts"

    id = Column(String, primary_key=True)
    email = Column(String)
    name = Column(String)
    picture = Column(String)
    # Optional overrides for role-specific AI strategy text (NULL = use app default).
    system_prompt_buyer = Column(Text, nullable=True)
    system_prompt_seller = Column(Text, nullable=True)
    system_prompt_buyer_seller = Column(Text, nullable=True)
    # Billing: trial | pro (managed keys; usage in trial_tokens_used / pro_tokens_used)
    subscription_tier = Column(String, nullable=False, default="trial")
    trial_started_at = Column(DateTime, nullable=True)
    trial_messages_used = Column(Integer, nullable=False, default=0)  # legacy; not used for enforcement
    trial_tokens_used = Column(Integer, nullable=False, default=0)
    pro_billing_month = Column(String, nullable=True)  # "YYYY-MM" for rolling monthly counter
    pro_messages_used = Column(Integer, nullable=False, default=0)  # legacy
    pro_tokens_used = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
