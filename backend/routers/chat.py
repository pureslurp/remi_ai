from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from config import MAX_TOKENS
from database import SessionLocal, get_db
from deps.project_access import ProjectForUser
from models import Account, ChatMessage
from schemas.chat import ChatMessageOut, ChatRequest, DraftEmailRequest
from services import chat_llm
from services.chat_token_estimate import estimate_chat_preflight_billable
from services.llm_config import (
    coerce_llm_for_tier,
    list_llm_options,
    missing_key_message,
    model_display_name,
    pair_allowed_for_tier,
    provider_key_configured,
)
from services.usage_entitlements import (
    assert_chat_allowed,
    increment_usage_after_chat_completion,
    subscription_tier,
)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["chat"])


@router.get("/messages", response_model=List[ChatMessageOut])
def get_messages(project: ProjectForUser, db: Session = Depends(get_db)):
    return (
        db.query(ChatMessage)
        .filter_by(project_id=project.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )


@router.post("/chat")
async def chat(project: ProjectForUser, body: ChatRequest, request: Request, db: Session = Depends(get_db)):
    from services.context_builder import build_system_prompt, load_history

    project_id = project.id
    account = db.query(Account).filter_by(id=project.owner_id).first()
    if not account:
        raise HTTPException(status_code=500, detail="Account missing for project")

    opts = list_llm_options()
    if not opts.get("providers"):
        raise HTTPException(
            status_code=503,
            detail="No LLM API keys are configured on the server. Set ANTHROPIC_API_KEY and/or "
            "OPENAI_API_KEY and/or GEMINI_API_KEY (or GOOGLE_API_KEY) in the host environment.",
        )

    tier = subscription_tier(account)
    provider, model = coerce_llm_for_tier(
        tier,
        getattr(project, "llm_provider", None),
        getattr(project, "llm_model", None),
    )

    if not provider_key_configured(provider):
        raise HTTPException(status_code=503, detail=missing_key_message(provider))

    if not pair_allowed_for_tier(tier, provider, model):
        raise HTTPException(
            status_code=400,
            detail=f"Model not allowed for your plan: {model_display_name(provider, model)}",
        )

    system = build_system_prompt(project, account)
    history = load_history(project, db)
    user_message = body.message

    preflight = estimate_chat_preflight_billable(system, history, user_message, MAX_TOKENS)
    assert_chat_allowed(account, db, preflight)

    db.add(ChatMessage(project_id=project_id, role="user", content=user_message))
    db.commit()

    owner_id = project.owner_id

    async def event_stream():
        usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0}
        try:
            async for chunk in chat_llm.stream_chat(
                project_id,
                user_message,
                system,
                history,
                request,
                provider,
                model,
                usage_out=usage,
            ):
                yield chunk
        finally:
            s = SessionLocal()
            try:
                acc = s.get(Account, owner_id)
                if acc:
                    increment_usage_after_chat_completion(
                        acc, s, usage.get("input_tokens", 0), usage.get("output_tokens", 0)
                    )
                    s.commit()
            finally:
                s.close()

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/messages", status_code=204)
def clear_messages(project: ProjectForUser, db: Session = Depends(get_db)):
    db.query(ChatMessage).filter_by(project_id=project.id).delete()
    db.commit()


@router.post("/chat/draft-email")
def draft_email(project: ProjectForUser, body: DraftEmailRequest, db: Session = Depends(get_db)):
    from services.gmail_service import create_gmail_draft

    try:
        url = create_gmail_draft(to=body.to, subject=body.subject, body=body.body)
        return {"draft_url": url}
    except RuntimeError as e:
        raise HTTPException(400, str(e))
