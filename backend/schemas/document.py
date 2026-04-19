from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class DocumentOut(BaseModel):
    id: str
    project_id: str
    filename: str
    source: str
    drive_file_id: Optional[str]
    gmail_message_id: Optional[str]
    mime_type: Optional[str]
    size_bytes: Optional[int]
    created_at: datetime
    chunk_count: int = 0

    model_config = {"from_attributes": True}
