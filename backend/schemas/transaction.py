from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class KeyDateCreate(BaseModel):
    label: str
    due_date: datetime


class KeyDateUpdate(BaseModel):
    label: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class KeyDateOut(BaseModel):
    id: str
    transaction_id: str
    label: str
    due_date: datetime
    completed_at: Optional[datetime]

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    property_id: Optional[str] = None
    offer_price: Optional[float] = None
    earnest_money: Optional[float] = None
    contingencies: List[str] = []
    status: str = "active"
    offer_date: Optional[datetime] = None
    accepted_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    notes: Optional[str] = None


class TransactionUpdate(BaseModel):
    property_id: Optional[str] = None
    offer_price: Optional[float] = None
    earnest_money: Optional[float] = None
    contingencies: Optional[List[str]] = None
    status: Optional[str] = None
    offer_date: Optional[datetime] = None
    accepted_date: Optional[datetime] = None
    close_date: Optional[datetime] = None
    notes: Optional[str] = None


class TransactionOut(BaseModel):
    id: str
    project_id: str
    property_id: Optional[str]
    offer_price: Optional[float]
    earnest_money: Optional[float]
    contingencies: List[str]
    status: str
    offer_date: Optional[datetime]
    accepted_date: Optional[datetime]
    close_date: Optional[datetime]
    notes: Optional[str]
    created_at: datetime
    key_dates: List[KeyDateOut] = []

    model_config = {"from_attributes": True}
