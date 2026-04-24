"""Heuristic assignment of email threads to transactions (auto; manual preserved)."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from models import EmailThread, Project, Property, Transaction


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").lower().strip())


def _addr_tokens(prop: "Property | None") -> set[str]:
    if not prop:
        return set()
    parts = [
        prop.address or "",
        prop.city or "",
        prop.state or "",
        prop.zip_code or "",
    ]
    blob = " ".join(parts)
    out = set()
    for w in re.split(r"[^\w]+", blob):
        w = w.strip()
        if len(w) > 2:
            out.add(w.lower())
    return out


def _thread_text_blob(thread: "EmailThread") -> str:
    subj = thread.subject or ""
    parts = [subj]
    for m in thread.messages or []:
        parts.append(m.body_text or m.snippet or "")
    return _norm(" ".join(parts))


def _score_thread_for_transaction(
    thread: "EmailThread",
    tx: "Transaction",
) -> int:
    score = 0
    prop = tx.property
    blob = _thread_text_blob(thread)
    tokens = _addr_tokens(prop)
    if tokens:
        for t in tokens:
            if len(t) > 3 and t in blob:
                score += 12
        # street number + name chunk
        if prop and prop.address:
            a = _norm(prop.address)
            if a and a in blob:
                score += 40
    # Date window: any message within offer-14d .. close+30d
    ostart = (tx.offer_date or tx.accepted_date) - timedelta(days=14) if (tx.offer_date or tx.accepted_date) else None
    oend = (tx.close_date or tx.offer_date or datetime.utcnow()) + timedelta(days=30) if (
        tx.close_date or tx.offer_date
    ) else None
    if ostart and oend and thread.last_message_date:
        if ostart <= thread.last_message_date <= oend:
            score += 15
    return score


def apply_auto_email_thread_tags(db: Session, project: "Project", *, only_thread_ids: set[str] | None = None) -> int:
    """Re-score threads; set transaction_id for auto (never touches manual). Returns number updated."""
    from models import EmailThread, Transaction

    n = 0
    if not project.transactions:
        return 0

    q = db.query(EmailThread).filter_by(project_id=project.id)
    if only_thread_ids:
        q = q.filter(EmailThread.id.in_(only_thread_ids))
    threads = q.all()
    for thread in threads:
        if thread.tag_source == "manual":
            continue
        best: tuple[str | None, int] = (None, 0)
        for tx in project.transactions:
            s = _score_thread_for_transaction(thread, tx)
            if s > best[1]:
                best = (tx.id, s)
        tid, sc = best
        new_tid = tid if sc >= 25 else None
        if thread.transaction_id != new_tid or (new_tid and thread.tag_source != "auto"):
            thread.transaction_id = new_tid
            thread.tag_source = "auto" if new_tid else None
            n += 1
    # Caller commits (e.g. end of Gmail sync)
    if n:
        try:
            db.flush()
        except Exception:
            db.rollback()
            raise
    return n
