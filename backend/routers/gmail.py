from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import exists
from sqlalchemy.orm import Session

from database import get_db
from deps.project_access import ProjectForUser
from models import EmailMessage, EmailThread
from schemas.email import EmailThreadOut
from services.gmail_service import delete_synced_email_thread, sync_gmail


class EmailThreadTagBody(BaseModel):
    transaction_id: Optional[str] = None  # set null to clear; manual tag

router = APIRouter(prefix="/api/projects/{project_id}", tags=["gmail"])


@router.get("/emails", response_model=List[EmailThreadOut])
def list_emails(project: ProjectForUser, db: Session = Depends(get_db)):
    has_messages = exists().where(EmailMessage.thread_id == EmailThread.id)
    threads = (
        db.query(EmailThread)
        .filter_by(project_id=project.id)
        .filter(has_messages)
        .order_by(EmailThread.last_message_date.desc())
        .all()
    )
    return threads


@router.patch("/emails/{thread_id}", response_model=EmailThreadOut)
def tag_email_thread(
    project: ProjectForUser,
    thread_id: str,
    body: EmailThreadTagBody = Body(...),
    db: Session = Depends(get_db),
):
    """Manually set which transaction a thread belongs to. Persists on sync (manual = no auto overwrite)."""
    thread = (
        db.query(EmailThread)
        .filter_by(id=thread_id, project_id=project.id)
        .first()
    )
    if not thread:
        raise HTTPException(404, detail="Thread not found")
    if body.transaction_id is None or body.transaction_id == "":
        thread.transaction_id = None
        thread.tag_source = "manual"  # type: ignore[assignment]
    else:
        from models import Transaction

        ok = (
            db.query(Transaction)
            .filter_by(id=body.transaction_id, project_id=project.id)
            .first()
        )
        if not ok:
            raise HTTPException(400, detail="Invalid transaction for this project")
        thread.transaction_id = body.transaction_id
        thread.tag_source = "manual"  # type: ignore[assignment]
    db.commit()
    db.refresh(thread)
    return thread


@router.delete("/emails/{thread_id}", status_code=204)
def delete_email_thread(project: ProjectForUser, thread_id: str, db: Session = Depends(get_db)):
    if not delete_synced_email_thread(db, project_id=project.id, thread_id=thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return Response(status_code=204)


@router.post("/gmail/sync")
def trigger_gmail_sync(project: ProjectForUser, db: Session = Depends(get_db)):
    result = sync_gmail(project, db)
    return result
