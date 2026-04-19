from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps.project_access import ProjectForUser
from models import Property
from schemas.property import PropertyCreate, PropertyUpdate, PropertyOut

router = APIRouter(prefix="/api/projects/{project_id}/properties", tags=["properties"])


@router.get("", response_model=List[PropertyOut])
def list_properties(project: ProjectForUser, db: Session = Depends(get_db)):
    return db.query(Property).filter_by(project_id=project.id).all()


@router.post("", response_model=PropertyOut, status_code=201)
def create_property(project: ProjectForUser, body: PropertyCreate, db: Session = Depends(get_db)):
    prop = Property(project_id=project.id, **body.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.put("/{prop_id}", response_model=PropertyOut)
def update_property(
    project: ProjectForUser,
    prop_id: str,
    body: PropertyUpdate,
    db: Session = Depends(get_db),
):
    prop = db.get(Property, prop_id)
    if not prop or prop.project_id != project.id:
        raise HTTPException(404, "Property not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(prop, key, value)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{prop_id}", status_code=204)
def delete_property(project: ProjectForUser, prop_id: str, db: Session = Depends(get_db)):
    prop = db.get(Property, prop_id)
    if not prop or prop.project_id != project.id:
        raise HTTPException(404, "Property not found")
    db.delete(prop)
    db.commit()
