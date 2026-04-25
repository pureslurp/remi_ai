from pydantic import BaseModel
from typing import Optional


class PropertyCreate(BaseModel):
    address: str
    city: Optional[str] = None
    state: str = "MI"
    zip_code: Optional[str] = None
    reapi_property_id: Optional[str] = None
    mls_number: Optional[str] = None
    list_price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    status: str = "active"
    notes: Optional[str] = None


class PropertyUpdate(BaseModel):
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    reapi_property_id: Optional[str] = None
    mls_number: Optional[str] = None
    list_price: Optional[float] = None
    beds: Optional[int] = None
    baths: Optional[float] = None
    sqft: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class PropertyOut(BaseModel):
    id: str
    project_id: str
    address: str
    city: Optional[str]
    state: Optional[str]
    zip_code: Optional[str]
    reapi_property_id: Optional[str] = None
    mls_number: Optional[str]
    list_price: Optional[float]
    beds: Optional[int]
    baths: Optional[float]
    sqft: Optional[int]
    status: str
    notes: Optional[str]

    model_config = {"from_attributes": True}
