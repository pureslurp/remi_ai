from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_id = Column(String, ForeignKey("accounts.id"), nullable=False)
    name = Column(String, nullable=False)
    client_type = Column(String, nullable=False)  # "buyer" | "seller" | "buyer & seller"
    email_addresses = Column(JSON, default=list)
    phone = Column(String)
    notes = Column(Text)
    drive_folder_id = Column(String)
    drive_folder_name = Column(String)
    gmail_history_id = Column(String)
    gmail_keywords = Column(JSON, default=list)
    # "include" = subject must contain a keyword (when keywords non-empty); "exclude" = skip if subject matches any
    gmail_keyword_mode = Column(String, nullable=False, default="include")
    gmail_address_rules = Column(JSON, default=dict)  # per-address optional keywords + after_date
    last_gmail_sync = Column(DateTime)
    last_drive_sync = Column(DateTime)
    # Per-workspace LLM preference (nullable = server defaults from env at chat time)
    llm_provider = Column(String, nullable=True)
    llm_model = Column(String, nullable=True)
    # For client_type "buyer & seller": which single property is the home they are selling
    sale_property_id = Column(String, ForeignKey("properties.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("Account", backref="projects")

    messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    email_threads = relationship("EmailThread", back_populates="project", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="project", cascade="all, delete-orphan", foreign_keys="[Property.project_id]")
    transactions = relationship("Transaction", back_populates="project", cascade="all, delete-orphan")
    conversation_summary_row = relationship(
        "ProjectConversationSummary",
        back_populates="project",
        uselist=False,
        cascade="all, delete-orphan",
    )
