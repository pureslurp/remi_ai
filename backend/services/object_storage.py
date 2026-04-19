"""Optional Supabase Storage for raw document bytes (multi-device / cloud)."""

from __future__ import annotations

import re
from pathlib import Path

from config import (
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_STORAGE_BUCKET,
    SUPABASE_URL,
    PROJECTS_DIR,
    use_supabase_storage,
)


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
    """
    Persist raw bytes. Returns Supabase object key when using cloud storage,
    otherwise None (caller writes under PROJECTS_DIR).
    """
    if not use_supabase_storage():
        return None

    assert SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY

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


def delete_file(object_key: str | None, project_id: str, filename: str) -> None:
    if object_key and use_supabase_storage():
        from supabase import create_client

        client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        client.storage.from_(SUPABASE_STORAGE_BUCKET).remove([object_key])
        return
    path = PROJECTS_DIR / project_id / "docs" / filename
    if path.exists():
        path.unlink()
