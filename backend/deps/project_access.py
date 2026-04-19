from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps.auth import require_account
from models import Project


def project_for_current_user(
    project_id: str,
    db: Session = Depends(get_db),
    account_id: str = Depends(require_account),
) -> Project:
    project = db.get(Project, project_id)
    if not project or project.owner_id != account_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


ProjectForUser = Annotated[Project, Depends(project_for_current_user)]
