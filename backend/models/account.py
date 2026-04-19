from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

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
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
