"""Rolling conversation summary: older messages are summarized; last N are live in chat."""

from __future__ import annotations

import logging
import os
from datetime import datetime

from sqlalchemy.orm import Session

from config import BUDGET_HISTORY_MESSAGES
from models import ChatMessage, ProjectConversationSummary
from services.context_triage import _cheap_llm_string

logger = logging.getLogger("reco.memory")


def maybe_refresh_conversation_summary(db: Session, project_id: str) -> int:
    """
    If there are more than BUDGET_HISTORY_MESSAGES prior messages, ensure summary
    covers everything before the live window. Returns estimated triage tokens (0 for now).
    """
    msgs = (
        db.query(ChatMessage)
        .filter_by(project_id=project_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        .all()
    )
    n = len(msgs)
    if n <= BUDGET_HISTORY_MESSAGES:
        return 0

    # Live window in DB: last BUDGET_HISTORY_MESSAGES messages. Everything before is "old."
    old = msgs[:-BUDGET_HISTORY_MESSAGES]
    boundary = msgs[-BUDGET_HISTORY_MESSAGES - 1]  # n-11th, last before live

    row = db.get(ProjectConversationSummary, project_id)
    if row and row.covered_message_id == boundary.id and (row.summary_text or "").strip():
        return 0
    if not row:
        row = ProjectConversationSummary(project_id=project_id, summary_text="")
        db.add(row)

    body = "\n\n".join(f"{m.role.upper()}: {m.content}" for m in old)
    if len(body) > 100_000:
        body = body[-100_000:]

    prompt = (
        "Summarize the following real-estate client chat for an assistant. "
        "Be concise (under 2000 words). Key facts, decisions, and open items only. "
        "Chronological is fine. Chat:\n\n" + body
    )
    try:
        text = _cheap_llm_string(prompt, max_out_tokens=2048)
    except Exception as e:
        logger.exception("Summary LLM failed: %s", e)
        return 0
    if not (text or "").strip():
        return 0
    row.summary_text = (text or "").strip()
    row.covered_message_id = boundary.id
    row.updated_at = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return 0
