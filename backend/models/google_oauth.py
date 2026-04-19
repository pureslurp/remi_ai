from sqlalchemy import Column, ForeignKey, String, Text

from database import Base


class GoogleOAuthCredential(Base):
    """Google OAuth credentials JSON; primary key equals `accounts.id` (Google `sub`)."""

    __tablename__ = "google_oauth_credentials"

    id = Column(String, ForeignKey("accounts.id"), primary_key=True)
    credentials_json = Column(Text, nullable=False)
