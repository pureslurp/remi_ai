import logging
import re
from collections import Counter
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from models import Project, Document
from deps.google_creds import get_google_credentials
from services.document_service import process_bytes

logger = logging.getLogger("reco.drive")


class DriveFolderAccessError(Exception):
    """Folder not accessible with drive.file (not granted via Picker or revoked)."""


def extract_folder_id(url_or_id: str) -> str:
    match = re.search(r"/folders/([a-zA-Z0-9_-]+)", url_or_id)
    return match.group(1) if match else url_or_id.strip()


_MAX_FILES = 5000  # hard cap so a misconfigured folder graph can't OOM the worker.

_LIST_FIELDS = (
    "nextPageToken, files(id, name, mimeType, size, modifiedTime, "
    "md5Checksum, shortcutDetails)"
)


def _folder_metadata(drive, folder_id: str, resource_key: str | None = None) -> dict:
    kwargs: dict = {
        "fileId": folder_id,
        "fields": "id,name,mimeType,driveId",
        "supportsAllDrives": True,
    }
    if resource_key:
        kwargs["resourceKey"] = resource_key
    return drive.files().get(**kwargs).execute()


def _normalize_granted_files(raw) -> list[dict]:
    if not raw:
        return []
    out: list[dict] = []
    for item in raw:
        if isinstance(item, str) and item.strip():
            out.append({"id": item.strip()})
        elif isinstance(item, dict):
            fid = (item.get("id") or "").strip()
            if fid:
                entry = {"id": fid}
                rk = (item.get("resourceKey") or "").strip()
                if rk:
                    entry["resourceKey"] = rk
                out.append(entry)
    return out


def _get_file_metadata(drive, file_id: str, resource_key: str | None = None) -> dict | None:
    kwargs: dict = {
        "fileId": file_id,
        "fields": "id, name, mimeType, size, modifiedTime, md5Checksum",
        "supportsAllDrives": True,
    }
    if resource_key:
        kwargs["resourceKey"] = resource_key
    try:
        return drive.files().get(**kwargs).execute()
    except Exception:
        logger.exception("Drive: get metadata failed for %s", file_id)
        return None


def _list_kwargs(parent_id: str, shared_drive_id: str | None, page_token: str | None = None) -> dict:
    """Build files.list kwargs; shared-drive folders need corpora=drive + driveId."""
    kwargs: dict = {
        "q": f"'{parent_id}' in parents and trashed=false",
        "fields": _LIST_FIELDS,
        "pageSize": 100,
        "supportsAllDrives": True,
        "includeItemsFromAllDrives": True,
    }
    if shared_drive_id:
        kwargs["corpora"] = "drive"
        kwargs["driveId"] = shared_drive_id
    else:
        kwargs["corpora"] = "user"
    if page_token:
        kwargs["pageToken"] = page_token
    return kwargs


def _count_immediate_children(drive, folder_id: str, shared_drive_id: str | None) -> int:
    total = 0
    page_token = None
    while True:
        kwargs = _list_kwargs(folder_id, shared_drive_id, page_token)
        resp = drive.files().list(**kwargs).execute()
        total += len(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return total


def _list_all_files(drive, folder_id: str, shared_drive_id: str | None = None) -> list[dict]:
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
            kwargs = _list_kwargs(current, shared_drive_id, page_token)

            try:
                resp = drive.files().list(**kwargs).execute()
            except Exception as exc:
                from googleapiclient.errors import HttpError

                if current == folder_id and isinstance(exc, HttpError):
                    status = getattr(exc.resp, "status", None)
                    if status in (403, 404):
                        raise DriveFolderAccessError(
                            f"Drive folder not accessible (HTTP {status})"
                        ) from exc
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

    creds = get_google_credentials()
    drive = google_build("drive", "v3", credentials=creds)

    folder_id = extract_folder_id(project.drive_folder_id) if project.drive_folder_id else None
    folder_resource_key = getattr(project, "drive_folder_resource_key", None) or None
    granted = _normalize_granted_files(getattr(project, "drive_granted_files", None))
    shared_drive_id: str | None = None
    folder_name = project.drive_folder_name or folder_id or "Drive"

    if not folder_id and not granted:
        return {
            "synced": 0,
            "skipped": 0,
            "skip_reasons": {},
            "message": (
                "Choose a Drive folder, then use Select files to sync (required for Google drive.file access)."
            ),
        }

    if folder_id:
        try:
            folder_meta = _folder_metadata(drive, folder_id, folder_resource_key)
            folder_name = folder_meta.get("name") or folder_name
            shared_drive_id = folder_meta.get("driveId")
            logger.info(
                "Drive sync start project=%s folder=%s (%s) shared_drive_id=%s granted=%d",
                project.id,
                folder_id,
                folder_name,
                shared_drive_id or "my-drive",
                len(granted),
            )
        except Exception as exc:
            from googleapiclient.errors import HttpError

            if isinstance(exc, HttpError) and getattr(exc.resp, "status", None) in (403, 404):
                return {
                    "synced": 0,
                    "skipped": 0,
                    "skip_reasons": {},
                    "message": (
                        "Could not access this Drive folder. Choose the folder again in settings. "
                        "If you recently changed Google permissions, reconnect Google and re-select the folder."
                    ),
                }
            logger.exception("Drive: could not read folder metadata %s", folder_id)
            raise

    all_files: list[dict] = []
    seen_ids: set[str] = set()

    for entry in granted:
        fid = entry["id"]
        if fid in seen_ids:
            continue
        seen_ids.add(fid)
        meta = _get_file_metadata(drive, fid, entry.get("resourceKey"))
        if meta and meta.get("mimeType") != "application/vnd.google-apps.folder":
            all_files.append(meta)

    if folder_id:
        try:
            tree_files = _list_all_files(drive, folder_id, shared_drive_id)
        except DriveFolderAccessError:
            tree_files = []
        for f in tree_files:
            fid = f.get("id")
            if fid and fid not in seen_ids:
                seen_ids.add(fid)
                all_files.append(f)

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
    files_in_tree = len(all_files)
    msg = f"Synced {synced_count} new file(s), skipped {skipped_total}."
    if detail:
        msg = f"{msg} ({detail})"

    if synced_count == 0 and skipped_total == 0:
        child_count = -1
        if folder_id:
            try:
                child_count = _count_immediate_children(drive, folder_id, shared_drive_id)
            except Exception:
                child_count = -1
        logger.info(
            "Drive sync empty project=%s folder=%s children=%s files_in_tree=%s",
            project.id,
            folder_id,
            child_count,
            files_in_tree,
        )
        if files_in_tree == 0:
            if not granted:
                msg = (
                    f'Google drive.file access does not list folder contents for "{folder_name}". '
                    "Click Select files to sync, choose the PDFs in that folder (you can multi-select), then Sync Now."
                )
            elif child_count == 0:
                msg = (
                    f'Folder "{folder_name}" looks empty to the API, and no granted files were readable. '
                    "Use Select files to sync and pick the documents in Google Drive."
                )
            elif child_count > 0:
                msg = (
                    f'Found {child_count} item(s) in "{folder_name}" but no supported files in tree. '
                    "Use Select files to sync to grant access to specific PDFs/DOCX files."
                )
            else:
                msg = (
                    f'No supported files synced. Use Select files to sync for "{folder_name}", '
                    "then run Sync Now again."
                )

    return {
        "synced": synced_count,
        "skipped": skipped_total,
        "skip_reasons": dict(skip_reasons),
        "files_in_tree": files_in_tree,
        "message": msg,
    }
