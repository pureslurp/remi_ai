from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from deps.auth import CurrentAccount
from models import Account
from services.llm_config import list_llm_options_for_tier
from services.usage_entitlements import subscription_tier

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/options")
def llm_options(account_id: CurrentAccount, db: Session = Depends(get_db)):
    acc = db.get(Account, account_id)
    tier = subscription_tier(acc) if acc else "trial"
    return list_llm_options_for_tier(tier)
