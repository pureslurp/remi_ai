from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps.project_access import ProjectForUser
from models import Document
from schemas.document import DocumentOut
from services.drive_service import sync_drive

router = APIRouter(prefix="/api/projects/{project_id}", tags=["drive"])


@router.get("/drive/files", response_model=List[DocumentOut])
def list_drive_files(project: ProjectForUser, db: Session = Depends(get_db)):
    docs = (
        db.query(Document)
        .filter_by(project_id=project.id, source="drive")
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
def trigger_drive_sync(project: ProjectForUser, db: Session = Depends(get_db)):
    result = sync_drive(project, db)
    return result
