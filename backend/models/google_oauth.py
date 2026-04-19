from sqlalchemy import Column, String, Text

from database import Base


class GoogleOAuthCredential(Base):
    """Single-tenant Google OAuth user credentials (JSON) when using Postgres."""

    __tablename__ = "google_oauth_credentials"

    id = Column(String, primary_key=True)
    credentials_json = Column(Text, nullable=False)
