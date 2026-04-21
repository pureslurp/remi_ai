from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps.auth import require_account
from deps.project_access import ProjectForUser
from models import Account, Project, Property
from schemas.project import ProjectCreate, ProjectUpdate, ProjectOut
from services.llm_config import normalize_project_llm_for_account
from services.usage_entitlements import subscription_tier

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db), account_id: str = Depends(require_account)):
    return (
        db.query(Project)
        .filter(Project.owner_id == account_id)
        .order_by(Project.updated_at.desc())
        .all()
    )


FREE_TIER_CLIENT_LIMIT = 1


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    body: ProjectCreate,
    db: Session = Depends(get_db),
    account_id: str = Depends(require_account),
):
    acc = db.get(Account, account_id)
    tier = subscription_tier(acc) if acc else "trial"
    if tier == "trial":
        existing = db.query(Project).filter(Project.owner_id == account_id).count()
        if existing >= FREE_TIER_CLIENT_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "free_client_limit",
                    "message": f"Free accounts are limited to {FREE_TIER_CLIENT_LIMIT} client workspace. Upgrade to Pro for unlimited clients.",
                },
            )
    project = Project(**body.model_dump(), owner_id=account_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project: ProjectForUser):
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project: ProjectForUser,
    body: ProjectUpdate,
    db: Session = Depends(get_db),
    account_id: str = Depends(require_account),
):
    data = body.model_dump(exclude_unset=True)
    acc = db.get(Account, account_id)
    tier = subscription_tier(acc) if acc else "trial"
    if "llm_provider" in data or "llm_model" in data:
        lp = data.get("llm_provider", project.llm_provider)
        lm = data.get("llm_model", project.llm_model)
        np, nm = normalize_project_llm_for_account(lp, lm, tier)
        data["llm_provider"] = np
        data["llm_model"] = nm
    if "sale_property_id" in data:
        spid = data["sale_property_id"]
        if spid is not None:
            prop = db.get(Property, spid)
            if not prop or prop.project_id != project.id:
                raise HTTPException(status_code=400, detail="sale_property_id must belong to this project")
    for key, value in data.items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}", status_code=204)
def delete_project(project: ProjectForUser, db: Session = Depends(get_db)):
    db.delete(project)
    db.commit()
