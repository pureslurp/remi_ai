from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps.auth import require_account
from deps.project_access import ProjectForUser
from models import Project
from schemas.project import ProjectCreate, ProjectUpdate, ProjectOut

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), account_id: str = Depends(require_account)):
    return (
        db.query(Project)
        .filter(Project.owner_id == account_id)
        .order_by(Project.updated_at.desc())
        .all()
    )


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    account_id: str = Depends(require_account),
):
    project = Project(**body.model_dump(), owner_id=account_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: ProjectForUser):
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(project: ProjectForUser, body: ProjectUpdate, db: Session = Depends(get_db)):
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project: ProjectForUser, db: Session = Depends(get_db)):
    db.delete(project)
    db.commit()
