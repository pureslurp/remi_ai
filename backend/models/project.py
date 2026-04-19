from sqlalchemy import Column, String, Text, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    client_type = Column(String, nullable=False)  # "buyer" | "seller"
    email_addresses = Column(JSON, default=list)
    phone = Column(String)
    notes = Column(Text)
    drive_folder_id = Column(String)
    drive_folder_name = Column(String)
    gmail_history_id = Column(String)
    gmail_keywords = Column(JSON, default=list)
    gmail_address_rules = Column(JSON, default=dict)  # per-address optional keywords + after_date
    last_gmail_sync = Column(DateTime)
    last_drive_sync = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    messages = relationship("ChatMessage", back_populates="project", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    email_threads = relationship("EmailThread", back_populates="project", cascade="all, delete-orphan")
    properties = relationship("Property", back_populates="project", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="project", cascade="all, delete-orphan")
