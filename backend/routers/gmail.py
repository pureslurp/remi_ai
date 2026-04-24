from typing import List

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import exists
from sqlalchemy.orm import Session

from database import get_db
from deps.project_access import ProjectForUser
from models import EmailMessage, EmailThread
from schemas.email import EmailThreadOut
from services.gmail_service import delete_synced_email_thread, sync_gmail

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


@router.delete("/emails/{thread_id}", status_code=204)
def delete_email_thread(project: ProjectForUser, thread_id: str, db: Session = Depends(get_db)):
    if not delete_synced_email_thread(db, project_id=project.id, thread_id=thread_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return Response(status_code=204)


@router.post("/gmail/sync")
def trigger_gmail_sync(project: ProjectForUser, db: Session = Depends(get_db)):
    result = sync_gmail(project, db)
    return result
