from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, ChatMessage
from schemas.chat import ChatMessageOut, ChatRequest, DraftEmailRequest
from services.claude_service import stream_chat

router = APIRouter(prefix="/api/projects/{project_id}", tags=["chat"])


def _get_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/messages", response_model=List[ChatMessageOut])
def get_messages(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    return (
        db.query(ChatMessage)
        .filter_by(project_id=project_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


@router.post("/chat")
async def chat(project_id: str, body: ChatRequest, request: Request, db: Session = Depends(get_db)):
    project = _get_project(project_id, db)

    # Build context and persist user message while db session is still open
    from services.context_builder import build_system_prompt, load_history
    from models import ChatMessage as CM
    system = build_system_prompt(project)
    history = load_history(project, db)
    db.add(CM(project_id=project_id, role="user", content=body.message))
    db.commit()

    async def event_stream():
        async for chunk in stream_chat(project_id, body.message, system, history, request):
            yield chunk

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/messages", status_code=204)
def clear_messages(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    db.query(ChatMessage).filter_by(project_id=project_id).delete()
    db.commit()


@router.post("/chat/draft-email")
def draft_email(project_id: str, body: DraftEmailRequest, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    from services.gmail_service import create_gmail_draft
    try:
        url = create_gmail_draft(to=body.to, subject=body.subject, body=body.body)
        return {"draft_url": url}
    except RuntimeError as e:
        raise HTTPException(400, str(e))
