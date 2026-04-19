from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, EmailThread
from schemas.email import EmailThreadOut
from services.gmail_service import sync_gmail

router = APIRouter(prefix="/api/projects/{project_id}", tags=["gmail"])


def _get_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/emails", response_model=List[EmailThreadOut])
def list_emails(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    threads = (
        db.query(EmailThread)
        .filter_by(project_id=project_id)
        .order_by(EmailThread.last_message_date.desc())
        .all()
    )
    return threads


@router.post("/gmail/sync")
def trigger_gmail_sync(project_id: str, db: Session = Depends(get_db)):
    project = _get_project(project_id, db)
    result = sync_gmail(project, db)
    return result
