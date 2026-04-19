import base64
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from sqlalchemy.orm import Session

from models import Project, EmailThread, EmailMessage, Document
from config import GOOGLE_SCOPES
from services.document_service import process_bytes
from services import google_token_store


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


def _decode_body(payload: dict) -> str:
    """Recursively extract text/plain body from a Gmail message payload."""
    mime = payload.get("mimeType", "")
    if mime == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""

    if mime.startswith("multipart/"):
        parts = payload.get("parts", [])
        for part in parts:
            text = _decode_body(part)
            if text:
                return text
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
        filename = payload.get("filename", "attachment")
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


def _effective_rule(project: Project, addr: str) -> tuple[list[str], datetime | None]:
    """
    Keywords + optional after_date for one client email address.
    Legacy: when gmail_address_rules is empty, all addresses use gmail_keywords.
    When rules exist but this address has no entry, still use gmail_keywords (gradual setup).
    When this address has an explicit entry, use its keywords (empty list = no subject filter).
    """
    addr_l = addr.strip().lower()
    norm = _normalize_rules_map(project.gmail_address_rules)
    if addr_l in norm:
        entry = norm[addr_l]
        kw = list(entry.get("keywords") or [])
        return (kw, _parse_after_date(entry.get("after_date")))
    return (list(project.gmail_keywords or []), None)


def _message_matches_address_rules(
    project: Project,
    subject: str,
    msg_date: datetime | None,
    from_addr: str,
    to_addrs: list[str],
) -> bool:
    """True if the message passes at least one matched client address's filters."""
    blob = " ".join([from_addr] + to_addrs).lower()
    matched = [ea for ea in project.email_addresses if ea.lower() in blob]
    if not matched:
        return False

    for ea in matched:
        keywords, after_dt = _effective_rule(project, ea)
        if keywords and not _subject_matches_keywords(subject, keywords):
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


def sync_gmail(project: Project, db: Session) -> dict:
    from googleapiclient.discovery import build as google_build

    if not project.email_addresses:
        return {"synced": 0, "message": "No email addresses configured for this client."}

    creds = _get_creds()
    gmail = google_build("gmail", "v1", credentials=creds)

    new_message_ids = []

    if project.gmail_history_id:
        # Incremental sync
        try:
            history_resp = gmail.users().history().list(
                userId="me",
                startHistoryId=project.gmail_history_id,
                historyTypes=["messageAdded"],
            ).execute()
            for record in history_resp.get("history", []):
                for msg in record.get("messagesAdded", []):
                    new_message_ids.append(msg["message"]["id"])
        except Exception:
            # historyId expired — fall back to full sync
            project.gmail_history_id = None
            db.commit()

    if not project.gmail_history_id:
        # Full sync: discover threads by address only; keywords/date are applied per message below
        query = _build_query(project.email_addresses, None)
        resp = gmail.users().threads().list(userId="me", q=query, maxResults=50).execute()
        threads = resp.get("threads", [])
        for t in threads:
            new_message_ids.append(t["id"])  # reuse id as thread_id for lookup

    synced_count = 0
    latest_history_id = project.gmail_history_id

    for msg_or_thread_id in new_message_ids:
        try:
            if project.gmail_history_id:
                # It's a message ID
                msg_data = gmail.users().messages().get(
                    userId="me", id=msg_or_thread_id, format="full"
                ).execute()
                thread_id = msg_data["threadId"]
            else:
                # It's a thread ID
                thread_id = msg_or_thread_id
                thread_data = gmail.users().threads().get(
                    userId="me", id=thread_id, format="full"
                ).execute()
                messages_data = thread_data.get("messages", [])

            # Fetch or update thread record
            thread_obj = db.get(EmailThread, thread_id)
            if not thread_obj:
                thread_obj = EmailThread(id=thread_id, project_id=project.id)
                db.add(thread_obj)

            msgs_to_process = [msg_data] if project.gmail_history_id else messages_data

            participants = set()
            latest_date = None

            for msg in msgs_to_process:
                msg_id = msg["id"]
                if db.get(EmailMessage, msg_id):
                    continue

                headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
                subject = headers.get("Subject", "")
                from_addr = headers.get("From", "")
                to_addrs = [a.strip() for a in headers.get("To", "").split(",")]
                date = _parse_date(headers.get("Date", ""))
                body = _decode_body(msg.get("payload", {}))
                snippet = msg.get("snippet", "")

                # Filter: only keep if involves client's email addresses
                all_addrs = [from_addr] + to_addrs
                if not any(
                    ea.lower() in " ".join(all_addrs).lower()
                    for ea in project.email_addresses
                ):
                    continue

                # Filter: per-address subject keywords and optional after-date
                if not _message_matches_address_rules(project, subject, date, from_addr, to_addrs):
                    continue

                thread_obj.subject = subject
                participants.update([from_addr] + to_addrs)
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

                # Extract attachments
                _extract_attachments(msg.get("payload", {}), msg_id, project.id, gmail, db)

                if msg.get("historyId"):
                    latest_history_id = msg["historyId"]

            thread_obj.participants = list(participants)
            if latest_date:
                thread_obj.last_message_date = latest_date
            thread_obj.fetched_at = datetime.utcnow()
            synced_count += 1

        except Exception as e:
            continue  # skip failed messages, don't break entire sync

    # Update history cursor
    if latest_history_id:
        project.gmail_history_id = latest_history_id
    project.last_gmail_sync = datetime.utcnow()
    db.commit()

    return {"synced": synced_count, "message": f"Synced {synced_count} threads/messages."}


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
