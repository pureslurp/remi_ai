import logging
import re
from collections import Counter
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from models import Project, Document
from config import GOOGLE_SCOPES
from services.document_service import process_bytes
from services import google_token_store

logger = logging.getLogger("kova.drive")


def _get_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if not google_token_store.credentials_exist():
        raise RuntimeError("Google not authenticated.")

    info = google_token_store.credentials_to_info()
    if not info:
        raise RuntimeError("Google not authenticated.")

    creds = Credentials.from_authorized_user_info(info, GOOGLE_SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        google_token_store.save_credentials_json(creds.to_json())
    if not creds.valid:
        raise RuntimeError("Google token expired. Reconnect Google in settings.")
    return creds


def extract_folder_id(url_or_id: str) -> str:
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


_MAX_FILES = 5000  # hard cap so a misconfigured folder graph can't OOM the worker.


def _list_all_files(drive, folder_id: str) -> list[dict]:
    """Iteratively list all non-trashed files under a Drive folder (incl. shared drives + shortcuts).

    Uses a visited-set so folder shortcuts that loop back (e.g. a shortcut inside a folder
    pointing to its ancestor) cannot recurse infinitely.
    """
    files: list[dict] = []
    visited: set[str] = set()
    seen_files: set[str] = set()  # de-dup file ids reached via multiple shortcut paths
    pending: list[str] = [folder_id]

    while pending:
        if len(files) >= _MAX_FILES:
            logger.warning("Drive: reached %d-file cap, stopping traversal", _MAX_FILES)
            break

        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)

        page_token = None
        while True:
            kwargs = dict(
                q=f"'{current}' in parents and trashed=false",
                fields=(
                    "nextPageToken, files(id, name, mimeType, size, modifiedTime, "
                    "md5Checksum, shortcutDetails)"
                ),
                pageSize=100,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
            )
            if page_token:
                kwargs["pageToken"] = page_token

            try:
                resp = drive.files().list(**kwargs).execute()
            except Exception:
                logger.exception("Drive: list failed for folder %s", current)
                break

            for f in resp.get("files", []):
                mt = f.get("mimeType")
                fid = f.get("id")
                if not fid:
                    continue

                if mt == "application/vnd.google-apps.folder":
                    if fid not in visited:
                        pending.append(fid)
                    continue

                if mt == "application/vnd.google-apps.shortcut":
                    sd = f.get("shortcutDetails") or {}
                    target_mime = sd.get("targetMimeType")
                    target_id = sd.get("targetId")
                    if not target_id:
                        continue
                    if target_mime == "application/vnd.google-apps.folder":
                        if target_id not in visited:
                            pending.append(target_id)
                        continue
                    if target_id in seen_files:
                        continue
                    try:
                        meta = (
                            drive.files()
                            .get(
                                fileId=target_id,
                                fields="id, name, mimeType, size, modifiedTime, md5Checksum",
                                supportsAllDrives=True,
                            )
                            .execute()
                        )
                    except Exception:
                        logger.exception("Drive: failed to resolve shortcut target %s", target_id)
                        continue
                    if meta.get("id") and meta["id"] not in seen_files:
                        seen_files.add(meta["id"])
                        files.append(meta)
                    continue

                if fid in seen_files:
                    continue
                seen_files.add(fid)
                files.append(f)

                if len(files) >= _MAX_FILES:
                    break

            page_token = resp.get("nextPageToken")
            if not page_token or len(files) >= _MAX_FILES:
                break

    return files


# Native (non-Workspace) types we ingest as-is.
DIRECT_SUPPORTED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # .docx
    "text/plain",
    "text/csv",
    "text/html",
    "application/rtf",
    "text/rtf",
}

# Google Workspace types we know how to export to text we can index.
# Map: source mime -> (export mime, output mime stored on the Document)
_WORKSPACE_EXPORT = {
    "application/vnd.google-apps.document": ("text/plain", "text/plain"),
    "application/vnd.google-apps.spreadsheet": ("text/csv", "text/csv"),
    "application/vnd.google-apps.presentation": ("text/plain", "text/plain"),
}

# Drive often labels uploaded Office files as octet-stream / zip; rescue by extension.
_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".html": "text/html",
    ".htm": "text/html",
    ".rtf": "application/rtf",
}

# Reasons surfaced to the UI when files are skipped.
REASON_UNSUPPORTED = "unsupported_type"
REASON_ALREADY_LINKED = "already_linked"
REASON_DUPLICATE_HASH = "duplicate_content"
REASON_DOWNLOAD_FAILED = "download_failed"
REASON_NO_TEXT = "extraction_empty"  # not used today, reserved


def _effective_mime(filename: str, declared: str) -> str:
    if declared in DIRECT_SUPPORTED_MIME or declared in _WORKSPACE_EXPORT:
        return declared
    ext = Path(filename or "").suffix.lower()
    if ext in _EXT_TO_MIME:
        return _EXT_TO_MIME[ext]
    return declared


def _download_file(drive, file: dict) -> tuple[bytes, str]:
    """Download a Drive file and return (content_bytes, stored_mime_type)."""
    mime = file["mimeType"]
    fid = file["id"]

    if mime in _WORKSPACE_EXPORT:
        export_mime, stored_mime = _WORKSPACE_EXPORT[mime]
        # files.export does not accept supportsAllDrives.
        content = drive.files().export(fileId=fid, mimeType=export_mime).execute()
        return content, stored_mime

    content = drive.files().get_media(fileId=fid, supportsAllDrives=True).execute()
    return content, mime


def sync_drive(project: Project, db: Session) -> dict:
    from googleapiclient.discovery import build as google_build

    if not project.drive_folder_id:
        return {
            "synced": 0,
            "skipped": 0,
            "skip_reasons": {},
            "message": "No Drive folder configured. Paste a folder URL in settings.",
        }

    creds = _get_creds()
    drive = google_build("drive", "v3", credentials=creds)

    folder_id = extract_folder_id(project.drive_folder_id)
    all_files = _list_all_files(drive, folder_id)

    synced_count = 0
    skip_reasons: Counter[str] = Counter()
    sample_unsupported: list[str] = []

    for f in all_files:
        name = f.get("name") or "(unnamed)"
        declared_mime = f.get("mimeType") or ""
        effective = _effective_mime(name, declared_mime)
        f_use = {**f, "mimeType": effective}

        if effective not in DIRECT_SUPPORTED_MIME and effective not in _WORKSPACE_EXPORT:
            skip_reasons[REASON_UNSUPPORTED] += 1
            if len(sample_unsupported) < 5:
                sample_unsupported.append(f"{name} ({declared_mime or 'unknown'})")
            logger.info("Drive skip [unsupported]: %s mime=%s", name, declared_mime)
            continue

        existing = db.query(Document).filter_by(
            project_id=project.id, drive_file_id=f["id"]
        ).first()
        if existing:
            skip_reasons[REASON_ALREADY_LINKED] += 1
            logger.info("Drive skip [already linked]: %s", name)
            continue

        try:
            content, stored_mime = _download_file(drive, f_use)
        except Exception as exc:
            skip_reasons[REASON_DOWNLOAD_FAILED] += 1
            logger.exception("Drive skip [download_failed]: %s mime=%s err=%s", name, effective, exc)
            continue

        try:
            result = process_bytes(
                project_id=project.id,
                filename=name,
                content=content,
                mime_type=stored_mime,
                source="drive",
                db=db,
                drive_file_id=f["id"],
            )
        except Exception as exc:
            skip_reasons[REASON_DOWNLOAD_FAILED] += 1
            logger.exception("Drive skip [process_failed]: %s err=%s", name, exc)
            continue

        if result:
            synced_count += 1
            logger.info("Drive sync ok: %s -> doc=%s", name, result.id)
        else:
            skip_reasons[REASON_DUPLICATE_HASH] += 1
            logger.info("Drive skip [duplicate hash]: %s", name)

    project.last_drive_sync = datetime.utcnow()
    db.commit()

    skipped_total = sum(skip_reasons.values())
    parts: list[str] = []
    if skip_reasons.get(REASON_UNSUPPORTED):
        sample = f" e.g. {', '.join(sample_unsupported)}" if sample_unsupported else ""
        parts.append(f"{skip_reasons[REASON_UNSUPPORTED]} unsupported type{sample}")
    if skip_reasons.get(REASON_ALREADY_LINKED):
        parts.append(f"{skip_reasons[REASON_ALREADY_LINKED]} already linked")
    if skip_reasons.get(REASON_DUPLICATE_HASH):
        parts.append(f"{skip_reasons[REASON_DUPLICATE_HASH]} duplicate content")
    if skip_reasons.get(REASON_DOWNLOAD_FAILED):
        parts.append(f"{skip_reasons[REASON_DOWNLOAD_FAILED]} download/processing failed (see server log)")

    detail = "; ".join(parts)
    msg = f"Synced {synced_count} new file(s), skipped {skipped_total}."
    if detail:
        msg = f"{msg} ({detail})"

    return {
        "synced": synced_count,
        "skipped": skipped_total,
        "skip_reasons": dict(skip_reasons),
        "message": msg,
    }
