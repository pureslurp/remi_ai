from sqlalchemy import Column, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from uuid import uuid4
from database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    property_id = Column(String, ForeignKey("properties.id"), nullable=True)
    offer_price = Column(Float)
    earnest_money = Column(Float)
    contingencies = Column(JSON, default=list)
    status = Column(String, default="active")  # active|pending|contingent|closed|dead
    offer_date = Column(DateTime)
    accepted_date = Column(DateTime)
    close_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="transactions")
    property = relationship("Property", back_populates="transactions")
    key_dates = relationship("KeyDate", back_populates="transaction", cascade="all, delete-orphan")


class KeyDate(Base):
    __tablename__ = "key_dates"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    transaction_id = Column(String, ForeignKey("transactions.id"), nullable=False)
    label = Column(String, nullable=False)
    due_date = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)

    transaction = relationship("Transaction", back_populates="key_dates")
