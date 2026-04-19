from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class EmailMessageOut(BaseModel):
    id: str
    thread_id: str
    from_addr: Optional[str]
    to_addrs: List[str]
    date: Optional[datetime]
    snippet: Optional[str]

    model_config = {"from_attributes": True}


class EmailThreadOut(BaseModel):
    id: str
    project_id: str
    subject: Optional[str]
    participants: List[str]
    last_message_date: Optional[datetime]
    fetched_at: datetime
    messages: List[EmailMessageOut] = []

    model_config = {"from_attributes": True}
