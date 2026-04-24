from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessageOut(BaseModel):
    id: str
    project_id: str
    role: str
    content: str
    created_at: datetime
    referenced_items: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ChatAttachmentIn(BaseModel):
    type: Literal["document"] = "document"
    id: str = Field(..., min_length=1, max_length=128)


# Cap user input to bound Anthropic cost + prevent a single request from
# ballooning the context window. 50k chars ≈ 12k tokens, well under sonnet-4-6's
# 200k window but far beyond any realistic chat message.
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=50_000)
    attachments: list[ChatAttachmentIn] = Field(default_factory=list)


class DraftEmailRequest(BaseModel):
    to: str = Field(..., max_length=1_000)
    subject: str = Field(..., max_length=1_000)
    body: str = Field(..., max_length=50_000)
