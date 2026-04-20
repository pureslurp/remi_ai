from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from config import MAX_UPLOAD_BYTES
from database import get_db
from deps.project_access import ProjectForUser
from models import Document
from schemas.document import DocumentOut
from services import object_storage
from services.document_service import process_upload

router = APIRouter(prefix="/api/projects/{project_id}/documents", tags=["documents"])


@router.get("", response_model=List[DocumentOut])
def list_documents(project: ProjectForUser, db: Session = Depends(get_db)):
    docs = (
        db.query(Document)
        .filter_by(project_id=project.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    result = []
    for doc in docs:
        out = DocumentOut.model_validate(doc)
        out.chunk_count = len(doc.chunks)
        result.append(out)
    return result


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(project: ProjectForUser, file: UploadFile = File(...), db: Session = Depends(get_db)):
    from pathlib import Path as _Path

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_UPLOAD_BYTES // 1024 // 1024}MB limit")

    # Strip any path components from client-provided filename so nothing downstream
    # (DB, local disk write, storage key) has to re-sanitize or trust a traversal.
    safe_name = _Path(file.filename or "file").name or "file"

    doc = process_upload(
        project_id=project.id,
        filename=safe_name,
        content=content,
        mime_type=file.content_type,
        db=db,
    )
    return DocumentOut.model_validate(doc)


@router.delete("/{doc_id}", status_code=204)
def delete_document(project: ProjectForUser, doc_id: str, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if not doc or doc.project_id != project.id:
        raise HTTPException(404, "Document not found")

    object_storage.delete_file(doc.storage_object_key, project.id, doc.filename)

    db.delete(doc)
    db.commit()
