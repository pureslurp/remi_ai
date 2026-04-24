from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class GmailAddressRule(BaseModel):
    """Per-address Gmail sync filters. Empty keywords = no subject filter for that address."""

    keywords: List[str] = []
    # include: subject must contain one of keywords (when keywords non-empty).
    # exclude: skip message if subject contains any keyword (when keywords non-empty).
    keyword_mode: str = "include"
    after_date: Optional[str] = None  # YYYY-MM-DD; only sync messages on/after this date


class ProjectCreate(BaseModel):
    name: str
    client_type: str  # "buyer" | "seller" | "buyer & seller"
    email_addresses: List[str] = []
    phone: Optional[str] = None
    notes: Optional[str] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client_type: Optional[str] = None
    email_addresses: Optional[List[str]] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    drive_folder_id: Optional[str] = None
    drive_folder_name: Optional[str] = None
    gmail_keywords: Optional[List[str]] = None
    gmail_keyword_mode: Optional[str] = None
    gmail_address_rules: Optional[Dict[str, GmailAddressRule]] = None
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    sale_property_id: Optional[str] = None


class ProjectOut(BaseModel):
    id: str
    name: str
    client_type: str
    email_addresses: List[str]
    phone: Optional[str]
    notes: Optional[str]
    drive_folder_id: Optional[str]
    drive_folder_name: Optional[str]
    gmail_keywords: Optional[List[str]] = Field(default_factory=list)
    gmail_keyword_mode: Optional[str] = "include"
    gmail_address_rules: Optional[Dict[str, GmailAddressRule]] = Field(default_factory=dict)
    last_gmail_sync: Optional[datetime]
    last_drive_sync: Optional[datetime]
    llm_provider: Optional[str] = None
    llm_model: Optional[str] = None
    sale_property_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime]

    model_config = {"from_attributes": True}
