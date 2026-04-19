from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, Document
from schemas.document import DocumentOut
from services.drive_service import sync_drive

router = APIRouter(prefix="/api/projects/{project_id}", tags=["drive"])


def _get_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("/drive/files", response_model=List[DocumentOut])
def list_drive_files(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    docs = (
        db.query(Document)
        .filter_by(project_id=project_id, source="drive")
        .order_by(Document.created_at.desc())
        .all()
    )
    result = []
    for doc in docs:
        out = DocumentOut.model_validate(doc)
        out.chunk_count = len(doc.chunks)
        result.append(out)
    return result


@router.post("/drive/sync")
def trigger_drive_sync(project_id: str, db: Session = Depends(get_db)):
    project = _get_project(project_id, db)
    result = sync_drive(project, db)
    return result
