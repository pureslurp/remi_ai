"""Cheap-model triage: pick relevant document and email thread IDs for chat context."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.orm import Session, joinedload

from config import EMAIL_TRIAGE_DAYS, TRIAGE_MAX_EMAIL_THREADS
from models import EmailThread, Project
from services.llm_config import (
    anthropic_api_key,
    gemini_api_key,
    openai_api_key,
    provider_key_configured,
)

logger = logging.getLogger("reco.triage")


@dataclass
class TriageOutcome:
    document_ids: list[str] = field(default_factory=list)
    email_thread_ids: list[str] = field(default_factory=list)
    triage_input_tokens_est: int = 0
    used_doc_triage: bool = False
    used_email_triage: bool = False
    fallbacks: list[str] = field(default_factory=list)


def _estimate_tokens(s: str) -> int:
    return max(8, len(s) // 4)


def _parse_json_list_ids(raw: str) -> list[str]:
    """Extract { "ids": ["..."] } or list from model output."""
    raw = (raw or "").strip()
    m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
    if m:
        try:
            j = json.loads(m.group(0))
            if isinstance(j, dict) and "ids" in j and isinstance(j["ids"], list):
                return [str(x) for x in j["ids"] if x]
        except json.JSONDecodeError:
            pass
    return []


def _cheap_llm_string(prompt: str, *, max_out_tokens: int = 1024) -> str:
    """Single non-streaming completion; pick first available provider with key."""
    if provider_key_configured("anthropic") and anthropic_api_key():
        from anthropic import Anthropic

        c = Anthropic(api_key=anthropic_api_key())
        r = c.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=max_out_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        parts: list[str] = []
        for b in r.content or []:
            if getattr(b, "type", None) == "text":
                parts.append(b.text)
        return "".join(parts)
    if provider_key_configured("openai") and openai_api_key():
        from openai import OpenAI

        o = OpenAI(api_key=openai_api_key())
        r = o.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=max_out_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        ch = r.choices[0] if r.choices else None
        return (ch.message.content or "") if ch else ""
    if provider_key_configured("gemini") and gemini_api_key():
        from google import genai
        from google.genai import types

        g = genai.Client(api_key=gemini_api_key())
        m = "gemini-2.0-flash"
        r = g.models.generate_content(
            model=m,
            contents=[types.Part.from_text(text=prompt)],
            config=types.GenerateContentConfig(max_output_tokens=max_out_tokens),
        )
        return (r.text or "") if r else ""
    raise RuntimeError("No LLM API key available for triage/summary")


def triage_document_ids(
    user_message: str, project: Project, db: Session, *, allow_triage: bool
) -> tuple[list[str] | None, int, int]:
    """
    Returns (ordered doc ids, triage est input toks, triage est output toks) or (None, 0, 0) to use recency fallback.
    """
    if not allow_triage or not user_message.strip():
        return None, 0, 0
    docs = sorted(
        (d for d in project.documents if d.chunks),
        key=lambda d: d.created_at or datetime.min,
        reverse=True,
    )
    if not docs:
        return None, 0, 0
    lines: list[str] = []
    for d in docs:
        fn = d.filename or "file"
        src = d.source or "?"
        summ = (d.short_summary or "").replace("\n", " ")[:400]
        lines.append(
            f"- id={d.id} filename={fn!r} source={src} created={d.created_at!s} "
            f"summary={summ!r}"
        )
    prompt = (
        "You are selecting which stored documents are relevant to the user question for a real-estate deal. "
        "Return JSON only: { \"ids\": [\"<document-uuid>\", ...] } ordered from most to least important. "
        "Include 0-8 ids; omit irrelevant docs. If no docs apply, { \"ids\": [] }.\n\n"
        f"USER_QUESTION: {user_message}\n\nDOCUMENTS:\n" + "\n".join(lines)
    )
    t_in = _estimate_tokens(prompt)
    try:
        out = _cheap_llm_string(prompt, max_out_tokens=512)
        t_out = _estimate_tokens(out)
    except Exception as e:
        logger.exception("Document triage failed: %s", e)
        return None, 0, 0
    ids = _parse_json_list_ids(out)
    valid = {d.id for d in docs}
    return [i for i in ids if i in valid][:8], t_in, t_out


def _active_transaction_ids(project: Project) -> set[str]:
    return {t.id for t in project.transactions if t.status not in ("closed", "dead")}


def _thread_sort_date(t: EmailThread) -> datetime:
    d = t.last_message_date
    if not d:
        return datetime.min
    if d.tzinfo is not None:
        return d.replace(tzinfo=None)
    return d


def prefilter_email_threads(project: Project, db: Session) -> list[EmailThread]:
    """Recency or transaction-tagged, capped."""
    all_threads = (
        db.query(EmailThread)
        .options(joinedload(EmailThread.messages))
        .filter(EmailThread.project_id == project.id)
        .all()
    )
    if not all_threads:
        return []
    active_tx = _active_transaction_ids(project)
    from datetime import timezone

    if EMAIL_TRIAGE_DAYS:
        cutoff = datetime.now(timezone.utc) - timedelta(days=EMAIL_TRIAGE_DAYS)
    else:
        cutoff = None
    out: list[EmailThread] = []
    seen: set[str] = set()
    for t in all_threads:
        if t.transaction_id in active_tx and t.id not in seen:
            out.append(t)
            seen.add(t.id)
        if len(out) >= TRIAGE_MAX_EMAIL_THREADS:
            return out
    for t in sorted(all_threads, key=_thread_sort_date, reverse=True):
        if len(out) >= TRIAGE_MAX_EMAIL_THREADS:
            break
        if t.id in seen:
            continue
        d = t.last_message_date
        if d is not None and cutoff is not None:
            d2 = d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            if d2 < cutoff:
                continue
        out.append(t)
        seen.add(t.id)
    return out


def triage_email_thread_ids(
    user_message: str, project: Project, db: Session, candidate_threads: list[EmailThread]
) -> tuple[list[str] | None, int, int]:
    if not user_message.strip() or not candidate_threads:
        return None, 0, 0
    lines = []
    for t in candidate_threads:
        pstr = ", ".join((t.participants or [])[:6]) if t.participants else ""
        snip = ""
        if t.messages:
            m0 = sorted(t.messages, key=lambda m: m.date or datetime.min)[-1] if t.messages else None
            if m0:
                snip = (m0.snippet or m0.body_text or "")[:200].replace("\n", " ")
        lines.append(
            f"- id={t.id!s} subject={t.subject!r} last={t.last_message_date!s} "
            f"tx={t.transaction_id!r} participants={pstr!r} snippet={snip!r}"
        )
    prompt = (
        "You are selecting which email threads are relevant to the user question. "
        "Return JSON only: { \"ids\": [\"<gmail-thread-id>\", ...] } ordered most to least important, "
        "0-20 ids. Chose by subject/dates/roles, not by reading full bodies.\n\n"
        f"USER_QUESTION: {user_message}\n\nTHREADS:\n" + "\n".join(lines)
    )
    t_in = _estimate_tokens(prompt)
    try:
        out = _cheap_llm_string(prompt, max_out_tokens=800)
        t_out = _estimate_tokens(out)
    except Exception as e:
        logger.exception("Email triage failed: %s", e)
        return None, 0, 0
    valid = {t.id for t in candidate_threads}
    ids = [i for i in _parse_json_list_ids(out) if i in valid][:20]
    return (ids or None, t_in, t_out)
