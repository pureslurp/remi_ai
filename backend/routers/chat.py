from __future__ import annotations

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from config import MAX_TOKENS
from database import SessionLocal, get_db
from deps.auth import require_account
from deps.project_access import ProjectForUser
from models import Account, ChatMessage, Document, EmailThread, Project, ProjectConversationSummary, Transaction
from schemas.chat import ChatMessageOut, ChatRequest, DraftEmailRequest
from services import chat_llm
from services.chat_token_estimate import estimate_chat_preflight_billable, estimate_context_token_breakdown
from services.context_builder import (
    build_context_system,
    build_document_index,
    build_documents_section,
    build_documents_section_by_ids,
    build_emails_section,
    build_emails_section_by_ids,
    get_conversation_summary_text,
    load_history,
)
from services.context_triage import prefilter_email_threads, triage_document_ids, triage_email_thread_ids
from services.conversation_memory import maybe_refresh_conversation_summary
from services.llm_config import (
    coerce_llm_for_tier,
    get_context_budgets,
    list_llm_options,
    missing_key_message,
    model_display_name,
    pair_allowed_for_tier,
    provider_key_configured,
)
from services.usage_entitlements import (
    assert_chat_allowed,
    increment_usage_after_chat_completion,
    is_admin,
    subscription_tier,
)

router = APIRouter(prefix="/api/projects/{project_id}", tags=["chat"])


def _load_project_for_chat(db: Session, project_id: str) -> Project | None:
    return (
        db.query(Project)
        .options(
            joinedload(Project.transactions).joinedload(
                Transaction.property,  # type: ignore[attr-defined]
            )
        )
        .options(joinedload(Project.transactions).joinedload(Transaction.key_dates))
        .options(joinedload(Project.documents).joinedload(Document.chunks))
        .options(joinedload(Project.email_threads).joinedload(EmailThread.messages))
        .filter_by(id=project_id)
        .first()
    )


def _referenced_for_api(
    referenced_items: dict | None, *, include_admin_usage: bool
) -> dict | None:
    if referenced_items is None:
        return None
    if include_admin_usage or "admin_usage" not in referenced_items:
        return referenced_items
    return {k: v for k, v in referenced_items.items() if k != "admin_usage"}


@router.get("/messages", response_model=List[ChatMessageOut])
def get_messages(
    project: ProjectForUser,
    db: Session = Depends(get_db),
    account_id: str = Depends(require_account),
):
    account = db.query(Account).filter_by(id=account_id).first()
    show_admin = bool(account and is_admin(account))
    rows = (
        db.query(ChatMessage)
        .filter_by(project_id=project.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    return [
        ChatMessageOut(
            id=m.id,
            project_id=m.project_id,
            role=m.role,
            content=m.content,
            created_at=m.created_at,
            referenced_items=_referenced_for_api(m.referenced_items, include_admin_usage=show_admin),
        )
        for m in rows
    ]


@router.post("/chat")
async def chat(project: ProjectForUser, body: ChatRequest, request: Request, db: Session = Depends(get_db)):
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

    p = _load_project_for_chat(db, project_id)
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    user_message = body.message
    extra_triage_in = 0
    ref_meta: dict = {
        "documents": [],
        "emails": [],
    }

    # Rolling summary for messages older than the live window
    try:
        maybe_refresh_conversation_summary(db, project_id)
    except Exception:
        pass

    conv_sum = get_conversation_summary_text(db, project_id)
    budgets = get_context_budgets(provider)
    b_docs = int(budgets.get("documents", 80_000))
    b_em = int(budgets.get("emails", 20_000))

    # --- Documents ---
    att_ids = [a.id for a in (body.attachments or []) if a.type == "document"]
    if att_ids:
        have = {d.id for d in p.documents}
        bad = set(att_ids) - have
        if bad:
            raise HTTPException(400, detail="Unknown document id in attachments")

    doc_t_in = doc_t_out = 0
    if att_ids:
        d_sec = build_documents_section_by_ids(p, att_ids, b_docs, also_index=True)
        for did in att_ids:
            d = next((x for x in p.documents if x.id == did), None)
            if d:
                ref_meta["documents"].append(
                    {"id": did, "label": d.filename, "source": d.source or ""}
                )
    elif p.documents:
        t_ids, doc_t_in, doc_t_out = triage_document_ids(
            user_message, p, db, allow_triage=True
        )
        if t_ids and len(t_ids) > 0:
            d_sec = build_documents_section_by_ids(
                p, t_ids, b_docs, also_index=True
            )
            for did in t_ids:
                d = next((x for x in p.documents if x.id == did), None)
                if d:
                    ref_meta["documents"].append(
                        {
                            "id": did,
                            "label": d.filename,
                            "source": d.source,
                        }
                    )
        else:
            d_sec = build_documents_section(p, b_docs)
            ref_meta["doc_fallback"] = "recency"
    else:
        d_sec = "No documents."

    # --- Emails: triage when we have a candidate pool ---
    e_cand = prefilter_email_threads(p, db)
    t_eids: list[str] | None = None
    e_t_in = e_t_out = 0
    if e_cand:
        t_eids, e_t_in, e_t_out = triage_email_thread_ids(
            user_message, p, db, e_cand
        )
        tmap = {t.id: t for t in e_cand}
        if t_eids and len(t_eids) > 0:
            e_sec = build_emails_section_by_ids(p, t_eids, b_em)
            for tid in t_eids:
                th = tmap.get(tid)
                if th:
                    ref_meta["emails"].append(
                        {
                            "id": tid,
                            "label": th.subject or "(no subject)",
                            "date": th.last_message_date.isoformat() if th.last_message_date else "",
                        }
                    )
        else:
            e_sec = build_emails_section(p, b_em)
            ref_meta["email_fallback"] = "recency"
    else:
        e_sec = build_emails_section(p, b_em)
        if p.email_threads:
            ref_meta["email_fallback"] = "recency"

    extra_triage_in = int(doc_t_in + e_t_in + (doc_t_out + e_t_out) // 3)

    system = build_context_system(
        p,
        account,
        d_sec,
        e_sec,
        conv_sum,
    )
    history = load_history(p, db)

    preflight = estimate_chat_preflight_billable(
        system, history, user_message, MAX_TOKENS, extra_triage_input_tokens=extra_triage_in
    )
    assert_chat_allowed(account, db, preflight)

    # Resolve before streaming: request `db` may close before the SSE generator runs.
    attach_admin_usage_for_stream = is_admin(account)

    # Token breakdown (dev: surfaced in response headers for debugging)
    triage_d = f"doc~{doc_t_in}+{doc_t_out}" if (doc_t_in or doc_t_out) else "doc=0"
    triage_e = f"email~{e_t_in}+{e_t_out}" if (e_t_in or e_t_out) else "email=0"
    preflight_d = f"{triage_d};{triage_e};triage_bill{extra_triage_in}"

    token_breakdown = estimate_context_token_breakdown(
        system, history, user_message, extra_triage_input_tokens=extra_triage_in
    )

    db.add(ChatMessage(project_id=project_id, role="user", content=user_message))
    db.commit()

    # Ensure referenced for assistant: triage + fallback disclosure
    ref_meta["triage"] = {
        "documents_triage": not bool(att_ids) and bool(p.documents),
        "emails_triage": bool(e_cand),
    }

    owner_id = p.owner_id

    async def event_stream():
        usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "triage_billable_in": extra_triage_in}
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
                assistant_referenced=ref_meta,
                attach_admin_usage=attach_admin_usage_for_stream,
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

    headers = {
        "X-Context-Breakdown": preflight_d,
        "X-Context-Tokens": json.dumps(token_breakdown),
    }
    return StreamingResponse(
        event_stream(), media_type="text/event-stream", headers=headers
    )


@router.delete("/messages", status_code=204)
def clear_messages(project: ProjectForUser, db: Session = Depends(get_db)):
    s = (
        db.query(ProjectConversationSummary)
        .filter_by(project_id=project.id)
        .first()
    )
    if s:
        db.delete(s)
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
