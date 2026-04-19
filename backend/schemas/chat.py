from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChatMessageOut(BaseModel):
    id: str
    project_id: str
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str


class DraftEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
