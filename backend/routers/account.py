from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from deps.auth import CurrentAccount
from models import Account
from schemas.account_settings import SystemPromptsOut, SystemPromptsUpdate, normalize_override_updates
from services.context_builder import default_strategy_prompts_for_api

router = APIRouter(prefix="/api/account", tags=["account"])

_OVERRIDE_ATTR = {
    "override_buyer": "system_prompt_buyer",
    "override_seller": "system_prompt_seller",
    "override_buyer_seller": "system_prompt_buyer_seller",
}


@router.get("/system-prompts", response_model=SystemPromptsOut)
def get_system_prompts(account_id: CurrentAccount, db: Session = Depends(get_db)):
    acc = db.query(Account).filter_by(id=account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    d = default_strategy_prompts_for_api()
    return SystemPromptsOut(
        default_buyer=d["default_buyer"],
        default_seller=d["default_seller"],
        default_buyer_seller=d["default_buyer_seller"],
        override_buyer=acc.system_prompt_buyer,
        override_seller=acc.system_prompt_seller,
        override_buyer_seller=acc.system_prompt_buyer_seller,
    )


@router.put("/system-prompts", response_model=SystemPromptsOut)
def put_system_prompts(
    account_id: CurrentAccount,
    body: SystemPromptsUpdate,
    db: Session = Depends(get_db),
):
    acc = db.query(Account).filter_by(id=account_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")

    updates = normalize_override_updates(body)
    for key, val in updates.items():
        setattr(acc, _OVERRIDE_ATTR[key], val)
    db.commit()
    db.refresh(acc)

    d = default_strategy_prompts_for_api()
    return SystemPromptsOut(
        default_buyer=d["default_buyer"],
        default_seller=d["default_seller"],
        default_buyer_seller=d["default_buyer_seller"],
        override_buyer=acc.system_prompt_buyer,
        override_seller=acc.system_prompt_seller,
        override_buyer_seller=acc.system_prompt_buyer_seller,
    )
