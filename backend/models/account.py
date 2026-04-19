from datetime import datetime

from sqlalchemy import Column, DateTime, String

from database import Base


class Account(Base):
    """Google user (OIDC `sub`) — one row per person using the app."""

    __tablename__ = "accounts"

    id = Column(String, primary_key=True)
    email = Column(String)
    name = Column(String)
    picture = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
