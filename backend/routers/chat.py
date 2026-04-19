from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from database import get_db
from deps.project_access import ProjectForUser
from models import ChatMessage
from schemas.chat import ChatMessageOut, ChatRequest, DraftEmailRequest
from services.claude_service import stream_chat

router = APIRouter(prefix="/api/projects/{project_id}", tags=["chat"])


@router.get("/messages", response_model=List[ChatMessageOut])
def get_messages(project: ProjectForUser, db: Session = Depends(get_db)):
    return (
        db.query(ChatMessage)
        .filter_by(project_id=project.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


@router.post("/chat")
async def chat(project: ProjectForUser, body: ChatRequest, request: Request, db: Session = Depends(get_db)):
    from services.context_builder import build_system_prompt, load_history

    system = build_system_prompt(project)
    history = load_history(project, db)
    db.add(ChatMessage(project_id=project.id, role="user", content=body.message))
    db.commit()

    async def event_stream():
        async for chunk in stream_chat(project.id, body.message, system, history, request):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/messages", status_code=204)
def clear_messages(project: ProjectForUser, db: Session = Depends(get_db)):
    db.query(ChatMessage).filter_by(project_id=project.id).delete()
    db.commit()


@router.post("/chat/draft-email")
def draft_email(project: ProjectForUser, body: DraftEmailRequest, db: Session = Depends(get_db)):
    from services.gmail_service import create_gmail_draft

    try:
        url = create_gmail_draft(to=body.to, subject=body.subject, body=body.body)
        return {"draft_url": url}
    except RuntimeError as e:
        raise HTTPException(400, str(e))
