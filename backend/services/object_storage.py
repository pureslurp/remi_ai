"""Optional Supabase Storage for raw document bytes (multi-device / cloud).

Storage is treated as best-effort: if the Supabase URL/key are misconfigured or the
bucket is temporarily unreachable, callers should still be able to ingest a document
(text extraction + chunking is the source of truth for the AI). All public functions
return `None` on failure and log once per process to avoid log spam.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from config import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
    PROJECTS_DIR,
    use_supabase_storage,
)

logger = logging.getLogger("remi.storage")

_warned_invalid_config = False


def _is_valid_supabase_url(url: str | None) -> bool:
    return bool(url and url.startswith(("http://", "https://")))


def _config_ready() -> bool:
    """True only when storage is enabled AND the URL looks like a real URL."""
    global _warned_invalid_config
    if not use_supabase_storage():
        return False
    if not _is_valid_supabase_url(SUPABASE_URL):
        if not _warned_invalid_config:
            _warned_invalid_config = True
            logger.error(
                "SUPABASE_URL is not a valid http(s) URL (got %r). Document binaries "
                "will not be uploaded to Storage; ingest will still create DB rows. "
                "Set SUPABASE_URL=https://<project-ref>.supabase.co",
                (SUPABASE_URL or "")[:40] + ("…" if SUPABASE_URL and len(SUPABASE_URL) > 40 else ""),
            )
        return False
    return True


def _safe_segment(name: str, max_len: int = 180) -> str:
    base = Path(name).name
    cleaned = re.sub(r"[^a-zA-Z0-9._-]", "_", base).strip("._") or "file"
    return cleaned[:max_len]


def save_file(
    project_id: str,
    document_id: str,
    filename: str,
    content: bytes,
    mime_type: str | None,
) -> str | None:
    """Persist raw bytes. Returns Supabase object key on success, otherwise None.

    A None return means the caller should fall back to local disk (or skip storing
    the binary entirely on ephemeral platforms). Never raises — failures are logged.
    """
    if not _config_ready():
        return None

    try:
        from supabase import create_client

        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        key = f"{project_id}/{document_id}_{_safe_segment(filename)}"
        file_options = {
            "upsert": "true",
            "content-type": mime_type or "application/octet-stream",
        }
        client.storage.from_(SUPABASE_STORAGE_BUCKET).upload(
            key,
            content,
            file_options=file_options,
        )
        return key
    except Exception as exc:
        logger.warning(
            "Supabase Storage upload failed for %s (%s). Continuing without binary copy.",
            filename,
            exc,
        )
        return None


def delete_file(object_key: str | None, project_id: str, filename: str) -> None:
    if object_key and _config_ready():
        try:
            from supabase import create_client

            client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
            client.storage.from_(SUPABASE_STORAGE_BUCKET).remove([object_key])
            return
        except Exception as exc:
            logger.warning("Supabase Storage delete failed for %s (%s)", object_key, exc)
            return
    # Sanitize filename + containment check: the filename comes from a DB row
    # whose value originated from an untrusted upload / Drive / Gmail source.
    # Without this, a crafted filename like "../../remi.db" would resolve outside
    # the project's docs dir and unlink arbitrary host files.
    safe = _safe_segment(filename)
    docs_dir = (PROJECTS_DIR / project_id / "docs").resolve()
    try:
        path = (docs_dir / safe).resolve()
        path.relative_to(docs_dir)  # raises ValueError if outside docs_dir
    except (ValueError, OSError):
        logger.warning("Refusing to delete out-of-tree path for %s/%s", project_id, filename)
        return
    if path.exists():
        try:
            path.unlink()
        except OSError as exc:
            logger.warning("Local disk delete failed for %s (%s)", path, exc)
