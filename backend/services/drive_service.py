import re
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from models import Project, Document
from config import GOOGLE_SCOPES
from services.document_service import process_bytes
from services import google_token_store


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


def _list_all_files(drive, folder_id: str) -> list[dict]:
    """Recursively list all non-trashed files in a Drive folder."""
    files = []
    page_token = None
    while True:
        kwargs = dict(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, md5Checksum)",
            pageSize=100,
        )
        if page_token:
            kwargs["pageToken"] = page_token
        resp = drive.files().list(**kwargs).execute()
        for f in resp.get("files", []):
            if f["mimeType"] == "application/vnd.google-apps.folder":
                files.extend(_list_all_files(drive, f["id"]))
            else:
                files.append(f)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return files


SUPPORTED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "application/vnd.google-apps.document",
}

# Drive often reports Office uploads as application/octet-stream, application/zip (docx is a zip),
# or other generic types. Use the filename when the declared MIME is not one we handle.
_EXT_TO_MIME = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
}


def _effective_mime(filename: str, declared: str) -> str:
    if declared in SUPPORTED_MIME:
        return declared
    ext = Path(filename or "").suffix.lower()
    if ext in _EXT_TO_MIME:
        return _EXT_TO_MIME[ext]
    return declared


def _download_file(drive, file: dict) -> tuple[bytes, str]:
    """Download a Drive file and return (content_bytes, mime_type)."""
    mime = file["mimeType"]

    if mime == "application/vnd.google-apps.document":
        content = drive.files().export(fileId=file["id"], mimeType="text/plain").execute()
        return content, "text/plain"

    content = drive.files().get_media(fileId=file["id"]).execute()
    return content, mime


def sync_drive(project: Project, db: Session) -> dict:
    from googleapiclient.discovery import build as google_build

    if not project.drive_folder_id:
        return {"synced": 0, "message": "No Drive folder configured. Paste a folder URL in settings."}

    creds = _get_creds()
    drive = google_build("drive", "v3", credentials=creds)

    folder_id = extract_folder_id(project.drive_folder_id)
    all_files = _list_all_files(drive, folder_id)

    synced_count = 0
    skipped_count = 0

    for f in all_files:
        name = f.get("name") or ""
        effective = _effective_mime(name, f.get("mimeType") or "")
        f_use = {**f, "mimeType": effective}

        if f_use["mimeType"] not in SUPPORTED_MIME:
            skipped_count += 1
            continue

        # Check if already indexed by drive_file_id and not modified since
        existing = db.query(Document).filter_by(
            project_id=project.id, drive_file_id=f["id"]
        ).first()
        if existing:
            skipped_count += 1
            continue

        try:
            content, mime = _download_file(drive, f_use)
            result = process_bytes(
                project_id=project.id,
                filename=f["name"],
                content=content,
                mime_type=mime,
                source="drive",
                db=db,
                drive_file_id=f["id"],
            )
            if result:
                synced_count += 1
            else:
                skipped_count += 1
        except Exception:
            skipped_count += 1
            continue

    project.last_drive_sync = datetime.utcnow()
    db.commit()

    return {
        "synced": synced_count,
        "skipped": skipped_count,
        "message": f"Synced {synced_count} new files, skipped {skipped_count}.",
    }
