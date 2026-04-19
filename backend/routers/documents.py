from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, Document
from schemas.document import DocumentOut
from services.document_service import process_upload
from services import object_storage
from config import MAX_UPLOAD_BYTES

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


def _get_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("", response_model=List[DocumentOut])
def list_documents(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    docs = db.query(Document).filter_by(project_id=project_id).order_by(Document.created_at.desc()).all()
    result = []
    for doc in docs:
        out = DocumentOut.model_validate(doc)
        out.chunk_count = len(doc.chunks)
        result.append(out)
    return result


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _get_project(project_id, db)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES // 1024 // 1024}MB limit")

    doc = process_upload(project_id=project_id, filename=file.filename, content=content,
                         mime_type=file.content_type, db=db)
    return DocumentOut.model_validate(doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(project_id: str, doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc or doc.project_id != project_id:
        raise HTTPException(404, "Document not found")

    object_storage.delete_file(doc.storage_object_key, project_id, doc.filename)

    db.delete(doc)
    db.commit()
