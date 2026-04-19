from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, Property
from schemas.property import PropertyCreate, PropertyUpdate, PropertyOut

router = APIRouter(prefix="/api/projects/{project_id}/properties", tags=["properties"])


def _get_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.get("", response_model=List[PropertyOut])
def list_properties(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    return db.query(Property).filter_by(project_id=project_id).all()


@router.post("", response_model=PropertyOut, status_code=201)
def create_property(project_id: str, body: PropertyCreate, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    prop = Property(project_id=project_id, **body.model_dump())
    db.add(prop)
    db.commit()
    db.refresh(prop)
    return prop


@router.put("/{prop_id}", response_model=PropertyOut)
def update_property(project_id: str, prop_id: str, body: PropertyUpdate, db: Session = Depends(get_db)):
    prop = db.get(Property, prop_id)
    if not prop or prop.project_id != project_id:
        raise HTTPException(404, "Property not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(prop, key, value)
    db.commit()
    db.refresh(prop)
    return prop


@router.delete("/{prop_id}", status_code=204)
def delete_property(project_id: str, prop_id: str, db: Session = Depends(get_db)):
    prop = db.get(Property, prop_id)
    if not prop or prop.project_id != project_id:
        raise HTTPException(404, "Property not found")
    db.delete(prop)
    db.commit()
