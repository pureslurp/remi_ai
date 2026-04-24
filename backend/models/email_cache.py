from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class EmailThread(Base):
    __tablename__ = "email_threads"

    id = Column(String, primary_key=True)  # Gmail thread ID
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    subject = Column(String)
    participants = Column(JSON, default=list)
    last_message_date = Column(DateTime)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    transaction_id = Column(String, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True)
    # "auto" | "manual" — if manual, sync does not overwrite tag
    tag_source = Column(String, nullable=True)

    project = relationship("Project", back_populates="email_threads")
    transaction = relationship("Transaction", backref="email_threads", foreign_keys=[transaction_id])
    messages = relationship("EmailMessage", back_populates="thread", cascade="all, delete-orphan",
                            order_by="EmailMessage.date")


class EmailMessage(Base):
    __tablename__ = "email_messages"

    id = Column(String, primary_key=True)  # Gmail message ID
    thread_id = Column(String, ForeignKey("email_threads.id"), nullable=False)
    from_addr = Column(String)
    to_addrs = Column(JSON, default=list)
    date = Column(DateTime)
    body_text = Column(Text)
    snippet = Column(String)

    thread = relationship("EmailThread", back_populates="messages")
