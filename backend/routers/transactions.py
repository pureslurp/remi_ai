from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Project, Transaction, KeyDate
from schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionOut,
    KeyDateCreate, KeyDateUpdate, KeyDateOut,
)

router = APIRouter(prefix="/api/projects/{project_id}/transactions", tags=["transactions"])


def _get_project(project_id: str, db: Session):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


def _get_tx(project_id: str, tx_id: str, db: Session):
    tx = db.get(Transaction, tx_id)
    if not tx or tx.project_id != project_id:
        raise HTTPException(404, "Transaction not found")
    return tx


@router.get("", response_model=List[TransactionOut])
def list_transactions(project_id: str, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    return db.query(Transaction).filter_by(project_id=project_id).all()


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(project_id: str, body: TransactionCreate, db: Session = Depends(get_db)):
    _get_project(project_id, db)
    tx = Transaction(project_id=project_id, **body.model_dump())
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


@router.put("/{tx_id}", response_model=TransactionOut)
def update_transaction(project_id: str, tx_id: str, body: TransactionUpdate, db: Session = Depends(get_db)):
    tx = _get_tx(project_id, tx_id, db)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(tx, key, value)
    db.commit()
    db.refresh(tx)
    return tx


@router.delete("/{tx_id}", status_code=204)
def delete_transaction(project_id: str, tx_id: str, db: Session = Depends(get_db)):
    tx = _get_tx(project_id, tx_id, db)
    db.delete(tx)
    db.commit()


@router.post("/{tx_id}/dates", response_model=KeyDateOut, status_code=201)
def add_key_date(project_id: str, tx_id: str, body: KeyDateCreate, db: Session = Depends(get_db)):
    _get_tx(project_id, tx_id, db)
    kd = KeyDate(transaction_id=tx_id, **body.model_dump())
    db.add(kd)
    db.commit()
    db.refresh(kd)
    return kd


@router.put("/{tx_id}/dates/{date_id}", response_model=KeyDateOut)
def update_key_date(project_id: str, tx_id: str, date_id: str, body: KeyDateUpdate, db: Session = Depends(get_db)):
    _get_tx(project_id, tx_id, db)
    kd = db.get(KeyDate, date_id)
    if not kd or kd.transaction_id != tx_id:
        raise HTTPException(404, "Key date not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(kd, key, value)
    db.commit()
    db.refresh(kd)
    return kd


@router.delete("/{tx_id}/dates/{date_id}", status_code=204)
def delete_key_date(project_id: str, tx_id: str, date_id: str, db: Session = Depends(get_db)):
    _get_tx(project_id, tx_id, db)
    kd = db.get(KeyDate, date_id)
    if not kd or kd.transaction_id != tx_id:
        raise HTTPException(404, "Key date not found")
    db.delete(kd)
    db.commit()
