import base64
import html as html_module
import logging
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from sqlalchemy.orm import Session

from models import Project, EmailThread, EmailMessage, Document
from config import GOOGLE_SCOPES
from services.document_service import process_bytes
from services import google_token_store

logger = logging.getLogger("reco.gmail")


def _pg_safe_str(s: str | None) -> str:
    """Postgres text cannot contain NUL; Gmail / MIME data sometimes does."""
    if s is None:
        return ""
    return str(s).replace("\x00", "")


def _get_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not google_token_store.credentials_exist():
        raise RuntimeError("Google not authenticated. Connect Google in settings.")

    info = google_token_store.credentials_to_info()
    if not info:
        raise RuntimeError("Google not authenticated. Connect Google in settings.")

    creds = Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        google_token_store.save_credentials_json(creds.to_json())
    if not creds.valid:
        raise RuntimeError("Google token expired. Reconnect Google in settings.")
    return creds


def _strip_html_to_text(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = html_module.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _decode_body(payload: dict) -> str:
    """Recursively extract text/plain (preferred) or text/html from a Gmail message payload."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""

    if mime == "text/html":
        data = payload.get("body", {}).get("data", "")
        raw = base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""
        return _strip_html_to_text(raw)

    if mime.startswith("multipart/"):
        parts = payload.get("parts", [])
        plain = ""
        for part in parts:
            pm = part.get("mimeType", "")
            text = _decode_body(part)
            if not text:
                continue
            if pm == "text/plain":
                return text
            if pm == "text/html" and not plain:
                plain = text
        return plain
    return ""


def _extract_attachments(payload: dict, message_id: str, project_id: str,
                          gmail, db: Session):
    """Download and store PDF/DOCX attachments from a Gmail message."""
    SUPPORTED = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    mime = payload.get("mimeType", "")
    if mime in SUPPORTED:
        attachment_id = payload.get("body", {}).get("attachmentId")
        filename = _pg_safe_str(payload.get("filename") or "attachment") or "attachment"
        if attachment_id:
            att = gmail.users().messages().attachments().get(
                userId="me", messageId=message_id, id=attachment_id
            ).execute()
            data = base64.urlsafe_b64decode(att["data"] + "==")
            process_bytes(
                project_id=project_id, filename=filename, content=data,
                mime_type=mime, source="gmail", db=db, gmail_message_id=message_id,
            )

    for part in payload.get("parts", []):
        _extract_attachments(part, message_id, project_id, gmail, db)


def _build_query(email_addresses: list[str], keywords: list[str] | None = None) -> str:
    addr_parts = []
    for addr in email_addresses:
        addr_parts.append(f"from:{addr} OR to:{addr}")
    query = " OR ".join(addr_parts) if addr_parts else ""
    if keywords:
        kw_part = " OR ".join(f'subject:"{k}"' for k in keywords)
        query = f"({query}) AND ({kw_part})" if query else kw_part
    return query


def _subject_matches_keywords(subject: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    subject_lower = subject.lower()
    return any(kw.lower() in subject_lower for kw in keywords)


def _normalize_keyword_mode(raw: str | None) -> str:
    if (raw or "").strip().lower() == "exclude":
        return "exclude"
    return "include"


def _normalize_rules_map(raw: dict | None) -> dict[str, dict]:
    if not raw:
        return {}
    return {k.strip().lower(): v for k, v in raw.items() if isinstance(v, dict)}


def _parse_after_date(iso_date: str | None) -> datetime | None:
    if not iso_date or not str(iso_date).strip():
        return None
    try:
        d = datetime.strptime(str(iso_date).strip()[:10], "%Y-%m-%d")
        return d.replace(hour=0, minute=0, second=0, microsecond=0)
    except ValueError:
        return None


def _effective_rule(project: Project, addr: str) -> tuple[list[str], datetime | None, str]:
    """
    Keywords + optional after_date + keyword_mode for one client email address.

    Per-address entry: non-empty ``keywords`` overrides the global list; empty ``keywords`` inherits
    ``project.gmail_keywords`` so you can set e.g. exclude mode on the global phrases for one address.
    """
    addr_l = addr.strip().lower()
    norm = _normalize_rules_map(project.gmail_address_rules)
    global_kw = list(project.gmail_keywords or [])
    global_mode = _normalize_keyword_mode(getattr(project, "gmail_keyword_mode", None))
    if addr_l in norm:
        entry = norm[addr_l]
        local_kw = list(entry.get("keywords") or [])
        kw = local_kw if local_kw else global_kw
        mode = _normalize_keyword_mode(entry.get("keyword_mode"))
        return (kw, _parse_after_date(entry.get("after_date")), mode)
    return (global_kw, None, global_mode)


def _message_matches_address_rules(
    project: Project,
    subject: str,
    msg_date: datetime | None,
    from_addr: str,
    to_addrs: list[str],
    cc_addrs: list[str],
) -> bool:
    """True if the message passes at least one matched client address's filters."""
    blob = " ".join([from_addr] + to_addrs + cc_addrs).lower()
    matched = [ea for ea in project.email_addresses if ea.lower() in blob]
    if not matched:
        return False

    for ea in matched:
        keywords, after_dt, kw_mode = _effective_rule(project, ea)
        if keywords:
            subj_hit = _subject_matches_keywords(subject, keywords)
            if kw_mode == "exclude" and subj_hit:
                continue
            if kw_mode == "include" and not subj_hit:
                continue
        if after_dt is not None:
            if msg_date is None:
                continue
            if msg_date.replace(tzinfo=None) < after_dt:
                continue
        return True
    return False


def _parse_date(header_val: str) -> datetime | None:
    try:
        return parsedate_to_datetime(header_val).replace(tzinfo=None)
    except Exception:
        return None


def _history_message_ids_paginated(gmail, start_history_id: str) -> tuple[list[str], str | None]:
    """All history pages since start_history_id; last response's historyId is the next sync cursor."""
    ids: list[str] = []
    page_token: str | None = None
    final_mailbox_history_id: str | None = None
    while True:
        kwargs: dict = {
            "userId": "me",
            "startHistoryId": start_history_id,
            "historyTypes": ["messageAdded"],
            "maxResults": 500,
        }
        if page_token:
            kwargs["pageToken"] = page_token
        resp = gmail.users().history().list(**kwargs).execute()
        for record in resp.get("history", []):
            for m in record.get("messagesAdded", []):
                mid = m.get("message", {}).get("id")
                if mid:
                    ids.append(mid)
        if resp.get("historyId"):
            final_mailbox_history_id = resp["historyId"]
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return ids, final_mailbox_history_id


def _thread_ids_paginated(gmail, query: str, *, max_pages: int = 20, page_size: int = 100) -> list[str]:
    """Gmail search for threads matching query, up to max_pages of page_size each."""
    if not (query or "").strip():
        return []
    out: list[str] = []
    page_token: str | None = None
    for _ in range(max_pages):
        kwargs: dict = {"userId": "me", "q": query, "maxResults": page_size}
        if page_token:
            kwargs["pageToken"] = page_token
        resp = gmail.users().threads().list(**kwargs).execute()
        for t in resp.get("threads", []):
            tid = t.get("id")
            if tid:
                out.append(tid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return out


def sync_gmail(project: Project, db: Session) -> dict:
    from googleapiclient.discovery import build as google_build
    from googleapiclient.errors import HttpError

    if not project.email_addresses:
        return {
            "synced": 0,
            "threads_checked": 0,
            "message": "No email addresses configured for this client.",
        }

    creds = _get_creds()
    gmail = google_build("gmail", "v1", credentials=creds)

    history_message_ids: list[str] = []
    history_final_id: str | None = None

    if project.gmail_history_id:
        try:
            history_message_ids, history_final_id = _history_message_ids_paginated(
                gmail, project.gmail_history_id
            )
        except Exception as hist_exc:
            # historyId expired — fall back to full scan via thread search only
            logger.warning(
                "Gmail history.list failed (%s: %s); clearing cursor for full scan",
                type(hist_exc).__name__,
                hist_exc,
            )
            project.gmail_history_id = None
            db.commit()

    full_query = _build_query(project.email_addresses, None)
    thread_ids = _thread_ids_paginated(gmail, full_query) if full_query else []
    thread_ids = list(dict.fromkeys(thread_ids))

    # History = new message ids since cursor; thread search = Gmail query for client addresses (always).
    work_queue: list[tuple[str, bool]] = [(mid, True) for mid in history_message_ids]
    work_queue.extend((tid, False) for tid in thread_ids)

    messages_imported = 0
    threads_checked = len(work_queue)
    latest_history_id = project.gmail_history_id

    # In-session caches: Session.get() does NOT find pending (unflushed) objects, so we must track
    # what we've added this sync to avoid creating duplicate EmailThread/EmailMessage rows when the
    # same thread appears in both the history queue and the thread-search queue.
    thread_cache: dict[str, EmailThread] = {}
    seen_msg_ids: set[str] = set()

    n_skip_existing = 0
    n_skip_addr = 0
    n_skip_rules = 0
    n_skip_gone = 0  # History listed an id Gmail no longer returns (deleted / expunged) → 404 on get
    n_skip_dup = 0   # Same message/thread already processed earlier this sync
    n_batch_errors = 0

    for msg_or_thread_id, fetch_as_message in work_queue:
        try:
            if fetch_as_message:
                # Message id from users.history — can 404 after delete/trash empty
                try:
                    msg_data = gmail.users().messages().get(
                        userId="me", id=msg_or_thread_id, format="full"
                    ).execute()
                except HttpError as he:
                    if getattr(he.resp, "status", None) == 404:
                        n_skip_gone += 1
                        continue
                    raise
                thread_id = msg_data["threadId"]
            else:
                thread_id = msg_or_thread_id
                try:
                    thread_data = gmail.users().threads().get(
                        userId="me", id=thread_id, format="full"
                    ).execute()
                except HttpError as he:
                    if getattr(he.resp, "status", None) == 404:
                        n_skip_gone += 1
                        continue
                    raise
                messages_data = thread_data.get("messages", [])

            thread_obj = thread_cache.get(thread_id) or db.get(EmailThread, thread_id)

            msgs_to_process = [msg_data] if fetch_as_message else messages_data

            participants = set()
            latest_date = None

            for msg in msgs_to_process:
                msg_id = msg["id"]
                if msg_id in seen_msg_ids:
                    n_skip_dup += 1
                    continue
                if db.get(EmailMessage, msg_id):
                    seen_msg_ids.add(msg_id)
                    n_skip_existing += 1
                    continue

                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = _pg_safe_str(headers.get("Subject", ""))
                from_addr = _pg_safe_str(headers.get("From", ""))
                to_addrs = [_pg_safe_str(a.strip()) for a in headers.get("To", "").split(",") if a.strip()]
                cc_addrs = [_pg_safe_str(a.strip()) for a in headers.get("Cc", "").split(",") if a.strip()]
                date = _parse_date(headers.get("Date", ""))
                body = _pg_safe_str(_decode_body(msg.get("payload", {})))
                snippet = _pg_safe_str(msg.get("snippet", ""))

                # Filter: only keep if involves client's email addresses (From / To / Cc)
                all_addrs = [from_addr] + to_addrs + cc_addrs
                addr_blob = " ".join(all_addrs).lower()
                if not any(ea.lower() in addr_blob for ea in project.email_addresses):
                    n_skip_addr += 1
                    continue

                # Filter: per-address subject keywords and optional after-date
                if not _message_matches_address_rules(
                    project, subject, date, from_addr, to_addrs, cc_addrs
                ):
                    n_skip_rules += 1
                    continue

                if thread_obj is None:
                    thread_obj = EmailThread(id=thread_id, project_id=project.id)
                    db.add(thread_obj)
                    thread_cache[thread_id] = thread_obj

                thread_obj.subject = subject
                participants.update([from_addr] + to_addrs + cc_addrs)
                if date and (latest_date is None or date > latest_date):
                    latest_date = date

                db.add(EmailMessage(
                    id=msg_id,
                    thread_id=thread_id,
                    from_addr=from_addr,
                    to_addrs=to_addrs,
                    date=date,
                    body_text=body[:8000],  # cap per-message storage
                    snippet=snippet,
                ))
                seen_msg_ids.add(msg_id)
                messages_imported += 1

                # Extract attachments
                _extract_attachments(msg.get("payload", {}), msg_id, project.id, gmail, db)

                if msg.get("historyId"):
                    latest_history_id = msg["historyId"]

            if thread_obj is not None and (participants or latest_date):
                thread_obj.participants = list(participants)
                if latest_date:
                    thread_obj.last_message_date = latest_date
                thread_obj.fetched_at = datetime.utcnow()

        except Exception as batch_exc:
            n_batch_errors += 1
            logger.debug(
                "Gmail sync batch skip id=%r: %s: %s",
                msg_or_thread_id,
                type(batch_exc).__name__,
                batch_exc,
            )
            continue  # skip failed messages, don't break entire sync

    # Advance sync cursor: prefer mailbox historyId from history.list (Gmail-recommended), else last message.
    if history_final_id:
        project.gmail_history_id = history_final_id
    elif latest_history_id:
        project.gmail_history_id = latest_history_id
    project.last_gmail_sync = datetime.utcnow()
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    if messages_imported:
        msg = (
            f"Imported {messages_imported} new message(s). "
            f"({threads_checked} Gmail thread(s) checked.)"
        )
    elif threads_checked:
        msg = (
            f"No new messages matched your filters (checked {threads_checked} thread(s)). "
            "Tip: subject keywords or “on or after” dates can hide mail; "
            "only PDF/DOCX attachments appear under Documents."
        )
    else:
        msg = "No Gmail threads matched the client addresses."

    # Auto-tag threads to transactions (heuristic; does not override manual)
    try:
        from services.email_thread_tagging import apply_auto_email_thread_tags

        _tc = set(thread_cache.keys()) if thread_cache else set()
        apply_auto_email_thread_tags(
            db, project, only_thread_ids=_tc if _tc else None
        )
    except Exception as tag_exc:
        logger.exception("auto email thread tag failed: %s", tag_exc)

    return {"synced": messages_imported, "threads_checked": threads_checked, "message": msg}


def delete_synced_email_thread(db: Session, *, project_id: str, thread_id: str) -> bool:
    """Remove one stored Gmail thread for a project (messages, related doc rows). Does not touch Gmail."""
    thread = db.get(EmailThread, thread_id)
    if not thread or thread.project_id != project_id:
        return False

    try:
        mids = [m.id for m in db.query(EmailMessage).filter(EmailMessage.thread_id == thread_id).all()]
        if mids:
            doc_ids = [
                d.id
                for d in db.query(Document).filter(
                    Document.project_id == project_id,
                    Document.gmail_message_id.in_(mids),
                ).all()
            ]
        else:
            doc_ids = []

        if doc_ids:
            db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).delete(
                synchronize_session=False
            )
            db.query(Document).filter(Document.id.in_(doc_ids)).delete(synchronize_session=False)

        db.query(EmailMessage).filter(EmailMessage.thread_id == thread_id).delete(
            synchronize_session=False
        )
        db.query(EmailThread).filter(EmailThread.id == thread_id).delete(synchronize_session=False)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return True


def create_gmail_draft(to: str, subject: str, body: str) -> str:
    """Create a Gmail draft and return a link to open it."""
    import email.mime.text
    from googleapiclient.discovery import build as google_build

    creds = _get_creds()
    gmail = google_build("gmail", "v1", credentials=creds)

    msg = email.mime.text.MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft = gmail.users().drafts().create(
        userId="me", body={"message": {"raw": raw}}
    ).execute()

    draft_id = draft.get("id", "")
    return f"https://mail.google.com/mail/u/0/#drafts/{draft_id}"
