"""Parse /search and /comps chat commands; build RealEstateAPI request bodies (v1 heuristics)."""

from __future__ import annotations

import re
from typing import Any

# Conservative default column allowlist for CSV export (/v2/CSVBuilder).
# RealEstateAPI requires each `map[]` string to be **at least 3 characters** (see CSV Generator API).
# Use `propertyId` instead of `id` for the vendor property identifier column.
DEFAULT_CSV_MAP: list[str] = [
    "propertyId",
    "address",
    "city",
    "state",
    "zip",
    "beds",
    "baths",
    "livingSquareFeet",
    "mlsListingPrice",
    "estimatedValue",
    "lastSaleDate",
    "lastSalePrice",
]


def parse_slash_command(message: str) -> tuple[str | None, str | None]:
    """Return (command, tail) e.g. ('/search', '3 br in 48067') or (None, None)."""
    m = (message or "").strip()
    if not m or not m.startswith("/"):
        return None, None
    parts = m.split(maxsplit=1)
    c0 = parts[0].lower()
    if c0 == "/search" or c0 == "/comps":
        tail = (parts[1] if len(parts) > 1 else "").strip()
        return c0, tail
    return None, None


def build_property_search_body_from_nl(tail: str) -> dict[str, Any] | None:
    """Heuristic NL → /v2/PropertySearch. Requires a 5-digit zip in the tail to run (v1)."""
    t = (tail or "").lower()
    zip_m = re.search(r"\b(\d{5})\b", t)
    if not zip_m:
        return None
    body: dict[str, Any] = {
        "zip": zip_m.group(1),
        "state": "MI",
        "resultIndex": 0,
        "size": 20,
    }
    # beds: 3 br, 3 bed, 3 bedroom
    bed_m = re.search(r"\b(\d{1,2})\s*(?:bed|bedroom|br)\b", t, re.I)
    if bed_m:
        b = int(bed_m.group(1))
        body["beds_min"] = b
        body["beds_max"] = b
    if re.search(r"\b(for sale|active|mls|listing|listings)\b", t, re.I):
        body["mls_active"] = True
    return body


def parse_comps_extras(tail: str) -> dict[str, Any]:
    """Parse optional key=value for radius, days, max_results in comps tail (after address)."""
    ex: dict[str, Any] = {}
    for key, typ, pattern in [
        ("max_radius_miles", float, r"radius=([\d.]+)"),
        ("max_days_back", int, r"days=([\d]+)"),
        ("max_results", int, r"max_results=([\d]+)"),
    ]:
        m = re.search(pattern, tail, re.I)
        if m:
            try:
                ex[key] = typ(m.group(1))  # type: ignore[arg-type]
            except (ValueError, TypeError):
                pass
    return ex


def strip_comps_extras_for_address(tail: str) -> str:
    """Remove key=value tokens to leave free-form address text."""
    s = re.sub(
        r"\b(?:radius|days|max_results)=[\d.]+\b",
        " ",
        tail,
        flags=re.I,
    )
    return re.sub(r"\s+", " ", s).strip()


# Aliases: subject = use project subject; no call without resolution
COMPS_SUBJECT_ALIASES = frozenset(
    {
        "subject",
        "this",
        "this property",
        "default",
    }
)


def is_comps_subject_alias(s: str) -> bool:
    t = s.strip().lower()
    if not t:
        return False
    if t in COMPS_SUBJECT_ALIASES:
        return True
    return t == "this property" or t.replace(".", "") == "subject property"

