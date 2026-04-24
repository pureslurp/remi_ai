#!/usr/bin/env python3
"""Delete synced Gmail threads by exact subject (messages, doc chunks, gmail docs).

  cd backend && .venv/bin/python scripts/delete_email_threads_by_subject.py \\
    "Prospective Homes (Oakland County -- Bikeable)"

  Add --dry-run to only print counts.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy.orm import Session

from database import SessionLocal
from models import Document, DocumentChunk, EmailMessage, EmailThread


def run(db: Session, subject: str, *, dry_run: bool, contains: bool) -> None:
    q = db.query(EmailThread)
    if contains:
        threads = q.filter(EmailThread.subject.ilike(f"%{subject}%")).all()
    else:
        threads = q.filter(EmailThread.subject == subject).all()
    if not threads:
        print(f"No threads with subject={subject!r}")
        return

    tids = [t.id for t in threads]
    msgs = db.query(EmailMessage).filter(EmailMessage.thread_id.in_(tids)).all()
    mids = [m.id for m in msgs]

    doc_ids: list[str] = []
    for mid in mids:
        for d in db.query(Document).filter(Document.gmail_message_id == mid).all():
            doc_ids.append(d.id)

    print(
        f"Threads={len(tids)} messages={len(mids)} documents(with gmail_message_id)={len(doc_ids)}"
    )
    if dry_run:
        print("Dry run — no changes.")
        return

    if doc_ids:
        db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).delete(
            synchronize_session=False
        )
        db.query(Document).filter(Document.id.in_(doc_ids)).delete(synchronize_session=False)

    db.query(EmailMessage).filter(EmailMessage.thread_id.in_(tids)).delete(
        synchronize_session=False
    )
    db.query(EmailThread).filter(EmailThread.id.in_(tids)).delete(synchronize_session=False)
    db.commit()
    print("Done.")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("subject", help="Thread subject (exact unless --contains)")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--contains",
        action="store_true",
        help="Match subject case-insensitively as substring (SQL ILIKE)",
    )
    args = p.parse_args()

    db = SessionLocal()
    try:
        run(db, args.subject.strip(), dry_run=args.dry_run, contains=args.contains)
    finally:
        db.close()


if __name__ == "__main__":
    main()
