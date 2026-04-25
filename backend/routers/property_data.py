"""BFF for RealEstateAPI: autocomplete, search, comps, CSV (server key only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel, Field

from config import REAPI_ACTIVE, REALESTATEAPI_BACKEND
from deps.auth import require_account
from services.realestateapi_client import (
    fetch_autocomplete,
    fetch_csv_builder,
    fetch_property_comps_v3,
    fetch_property_search,
    format_comps_list_for_prompt,
    format_property_search_for_prompt,
)
from services.reapi_slash import DEFAULT_CSV_MAP
from services.realestateapi_rate_limit import check_rate_limit

router = APIRouter(prefix="/api/property-data", tags=["property-data"])

# Allowlist for BFF; `id` is accepted for back-compat but normalized to `propertyId` before the vendor call.
_ALLOWED_CSV: frozenset[str] = frozenset(
    list(DEFAULT_CSV_MAP)
    + [
        "id",
        "property_id",
        "bedrooms",
        "bathrooms",
    ]
)


def _normalize_csv_map_columns(cols: list[str]) -> list[str]:
    """Vendor requires each map entry length >= 3; alias short names to documented fields."""
    out: list[str] = []
    seen: set[str] = set()
    alias = {"id": "propertyId"}
    for raw in cols:
        c = (raw or "").strip()
        if not c:
            continue
        c = alias.get(c, c)
        if len(c) < 3:
            raise HTTPException(
                400,
                detail=f"CSV map column {c!r} is too short; each entry must be at least 3 characters per RealEstateAPI.",
            )
        if c not in _ALLOWED_CSV:
            raise HTTPException(400, detail=f"Column not allowed: {c}")
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def _require_reapi() -> None:
    if not REAPI_ACTIVE:
        if REALESTATEAPI_BACKEND:
            raise HTTPException(
                503,
                detail="Property data (RealEstateAPI) is disabled on this server.",
            )
        raise HTTPException(503, detail="RealEstateAPI is not configured on this server.")


class PropertyCompsIn(BaseModel):
    address: str | None = None
    id: str | None = None
    max_results: int | None = 10
    max_radius_miles: float | None = 2.0
    max_days_back: int | None = 365


class CsvExportIn(BaseModel):
    file_name: str = "export"
    map: list[str] = Field(default_factory=lambda: list(DEFAULT_CSV_MAP))
    ids: list[int] = Field(min_length=1, max_length=200)


@router.get("/autocomplete")
async def autocomplete(
    q: str = "",
    account_id: str = Depends(require_account),
):
    _require_reapi()
    s = (q or "").strip()
    if len(s) < 3:
        return {"data": None, "status": "min_length"}
    check_rate_limit(account_id)
    raw = await fetch_autocomplete(s)
    if not raw:
        return {"data": None}
    return raw


@router.post("/search")
async def property_search(
    body: dict[str, Any] = Body(...),
    account_id: str = Depends(require_account),
):
    _require_reapi()
    check_rate_limit(account_id)
    raw = await fetch_property_search(body)
    if not raw:
        raise HTTPException(502, detail="Property search failed or returned no data.")
    summary, ids = format_property_search_for_prompt(raw)
    return {
        "vendor": raw,
        "summary": summary,
        "export_ids": ids,
    }


@router.post("/comps")
async def property_comps(
    body: PropertyCompsIn,
    account_id: str = Depends(require_account),
):
    _require_reapi()
    check_rate_limit(account_id)
    if not (body.address and body.address.strip()) and not (body.id and str(body.id).strip()):
        raise HTTPException(400, detail="Provide a non-empty `address` or `id` (vendor property id).")
    raw = await fetch_property_comps_v3(
        address=body.address.strip() if body.address else None,
        property_id=body.id.strip() if body.id else None,
        max_results=body.max_results or 10,
        max_radius_miles=body.max_radius_miles or 2.0,
        max_days_back=body.max_days_back or 365,
    )
    if not raw:
        raise HTTPException(502, detail="Comps request failed or returned no data.")
    summary, export_ids = format_comps_list_for_prompt(raw)
    return {
        "vendor": raw,
        "summary": summary,
        "export_ids": export_ids,
    }


@router.post("/csv")
async def csv_export(
    body: CsvExportIn,
    account_id: str = Depends(require_account),
):
    _require_reapi()
    check_rate_limit(account_id)
    m = _normalize_csv_map_columns(list(body.map or []))
    if not m:
        raise HTTPException(400, detail="`map` must name at least one allowlisted column (each ≥ 3 characters).")
    raw = await fetch_csv_builder(
        {
            "file_name": (body.file_name or "export").replace("/", "_")[:80],
            "map": m,
            "ids": [int(x) for x in body.ids],
        }
    )
    if not raw or not isinstance(raw, dict):
        raise HTTPException(502, detail="CSV export request failed.")
    return raw
