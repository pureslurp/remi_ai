"""RealEstateAPI Property Detail client (server-side only).

See docs/real-estateapi-v1.md for scope and subscription notes.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

import httpx

from config import (
    REALESTATEAPI_BACKEND,
    REALESTATEAPI_BASE_URL,
    REALESTATEAPI_CACHE_TTL_SECONDS,
)

logger = logging.getLogger("reco")

_CACHE: dict[str, tuple[float, dict[str, Any] | None, str | None]] = {}
# value: (expires_at_monotonic, result_or_none, error_message_for_logs)

PROPERTY_DETAIL_PATH = "/v2/PropertyDetail"
# Customizable comps + AVM params (v2 PropertyDetail "comps: true" uses v2 under the hood; v3 is the direct API).
# See https://developer.realestateapi.com/reference/v3-comps-response-object
PROPERTY_COMPS_V3_PATH = "/v3/PropertyComps"
AUTOCOMPLETE_PATH = "/v2/AutoComplete"
PROPERTY_SEARCH_PATH = "/v2/PropertySearch"
CSV_BUILDER_PATH = "/v2/CSVBuilder"


def _cache_key(payload: dict[str, Any]) -> str:
    raw = repr(sorted(payload.items()))
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def _clear_expired() -> None:
    now = time.monotonic()
    dead = [k for k, v in _CACHE.items() if v[0] < now]
    for k in dead:
        _CACHE.pop(k, None)


async def fetch_property_detail(
    *,
    address: str | None = None,
    property_id: str | None = None,
    house: str | None = None,
    street: str | None = None,
    city: str | None = None,
    state: str | None = None,
    zip_code: str | None = None,
    include_comps: bool = False,
) -> dict[str, Any] | None:
    """POST PropertyDetail. Returns the parsed JSON object (full response) or None on soft failure.

    On HTTP errors or missing API key, returns None and logs at warning level.
    """
    if not REALESTATEAPI_BACKEND:
        return None

    body: dict[str, Any] = {"comps": include_comps}
    if property_id:
        body["id"] = str(property_id)
    elif address and address.strip():
        body["address"] = address.strip()
    else:
        if not (street and city and state and zip_code):
            return None
        if house and house.strip():
            body["house"] = house.strip()
        if street:
            body["street"] = street.strip()
        if city:
            body["city"] = city.strip()
        if state:
            body["state"] = state.strip()
        if zip_code:
            body["zip"] = str(zip_code).strip()

    ck = _cache_key(body)
    _clear_expired()
    if ck in _CACHE:
        exp, res, _ = _CACHE[ck]
        if exp >= time.monotonic() and isinstance(res, dict):
            return res

    url = f"{REALESTATEAPI_BASE_URL}{PROPERTY_DETAIL_PATH}"
    headers = {
        "x-api-key": REALESTATEAPI_BACKEND,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, json=body, headers=headers)
    except (httpx.HTTPError, OSError) as e:
        logger.warning("RealEstateAPI request failed: %s", e)
        return None

    if r.status_code == 200:
        try:
            data = r.json()
        except ValueError as e:
            logger.warning("RealEstateAPI invalid JSON: %s", e)
            return None
        exp = time.monotonic() + max(30, REALESTATEAPI_CACHE_TTL_SECONDS)
        _CACHE[ck] = (exp, data, None)
        return data

    logger.warning(
        "RealEstateAPI HTTP %s: %s",
        r.status_code,
        (r.text or "")[:500],
    )
    return None


async def fetch_property_comps_v3(
    *,
    address: str | None = None,
    property_id: str | None = None,
    max_results: int = 10,
    max_radius_miles: float = 2.0,
    max_days_back: int = 365,
    exact_match: bool = False,
    **extra: Any,
) -> dict[str, Any] | None:
    """POST /v3/PropertyComps — customizable comparable sales (separate from PropertyDetail).

    Per vendor docs, calling v3 directly may bill **1 credit per subject** (not per comp). Ensure
    your key's subscription includes this product.
    """
    if not REALESTATEAPI_BACKEND:
        return None
    if not (address and address.strip()) and not (property_id and str(property_id).strip()):
        return None

    body: dict[str, Any] = {
        "max_results": max(1, min(50, int(max_results))),
        "max_radius_miles": float(max(0.1, min(100.0, max_radius_miles))),
        "max_days_back": int(max_days_back),
        "exact_match": bool(exact_match),
    }
    if property_id:
        body["id"] = str(property_id)
    else:
        body["address"] = (address or "").strip()
    for k, v in extra.items():
        if v is not None:
            body[k] = v

    url = f"{REALESTATEAPI_BASE_URL}{PROPERTY_COMPS_V3_PATH}"
    headers = {
        "x-api-key": REALESTATEAPI_BACKEND,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=body, headers=headers)
    except (httpx.HTTPError, OSError) as e:
        logger.warning("RealEstateAPI v3 PropertyComps failed: %s", e)
        return None

    if r.status_code == 200:
        try:
            return r.json()
        except ValueError as e:
            logger.warning("RealEstateAPI v3 invalid JSON: %s", e)
            return None

    logger.warning(
        "RealEstateAPI v3 PropertyComps HTTP %s: %s",
        r.status_code,
        (r.text or "")[:500],
    )
    return None


async def fetch_autocomplete(
    search: str,
    *,
    search_types: list[str] | None = None,
) -> dict[str, Any] | None:
    """POST /v2/AutoComplete — min 3 chars. See vendor AutoComplete API."""
    if not REALESTATEAPI_BACKEND:
        return None
    s = (search or "").strip()
    if len(s) < 3:
        return None
    body: dict[str, Any] = {"search": s}
    if search_types:
        body["search_types"] = search_types
    url = f"{REALESTATEAPI_BASE_URL}{AUTOCOMPLETE_PATH}"
    headers = {
        "x-api-key": REALESTATEAPI_BACKEND,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, json=body, headers=headers)
    except (httpx.HTTPError, OSError) as e:
        logger.warning("RealEstateAPI AutoComplete failed: %s", e)
        return None
    if r.status_code == 200:
        try:
            return r.json()
        except ValueError as e:
            logger.warning("RealEstateAPI AutoComplete invalid JSON: %s", e)
            return None
    logger.warning("RealEstateAPI AutoComplete HTTP %s: %s", r.status_code, (r.text or "")[:500])
    return None


async def fetch_property_search(body: dict[str, Any]) -> dict[str, Any] | None:
    """POST /v2/PropertySearch — list building; pass vendor-shaped JSON."""
    if not REALESTATEAPI_BACKEND:
        return None
    b = dict(body)
    size = b.get("size", 20)
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 20
    b["size"] = max(1, min(50, size))
    ri = b.get("resultIndex", 0)
    try:
        b["resultIndex"] = max(0, int(ri))
    except (TypeError, ValueError):
        b["resultIndex"] = 0

    url = f"{REALESTATEAPI_BASE_URL}{PROPERTY_SEARCH_PATH}"
    headers = {
        "x-api-key": REALESTATEAPI_BACKEND,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(url, json=b, headers=headers)
    except (httpx.HTTPError, OSError) as e:
        logger.warning("RealEstateAPI PropertySearch failed: %s", e)
        return None
    if r.status_code == 200:
        try:
            return r.json()
        except ValueError as e:
            logger.warning("RealEstateAPI PropertySearch invalid JSON: %s", e)
            return None
    logger.warning("RealEstateAPI PropertySearch HTTP %s: %s", r.status_code, (r.text or "")[:500])
    return None


async def fetch_csv_builder(body: dict[str, Any]) -> dict[str, Any] | None:
    """POST /v2/CSVBuilder — request CSV export. Response shape is vendor-specific."""
    if not REALESTATEAPI_BACKEND:
        return None
    if not body.get("file_name") or not body.get("map"):
        return None
    url = f"{REALESTATEAPI_BASE_URL}{CSV_BUILDER_PATH}"
    headers = {
        "x-api-key": REALESTATEAPI_BACKEND,
        "content-type": "application/json",
        "accept": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            r = await client.post(url, json=body, headers=headers)
    except (httpx.HTTPError, OSError) as e:
        logger.warning("RealEstateAPI CSVBuilder failed: %s", e)
        return None
    if r.status_code == 200:
        try:
            return r.json()
        except ValueError as e:
            logger.warning("RealEstateAPI CSVBuilder invalid JSON: %s", e)
            return None
    logger.warning("RealEstateAPI CSVBuilder HTTP %s: %s", r.status_code, (r.text or "")[:500])
    return None


def _int_vendor_property_id(v: Any) -> int | None:
    if v is None or v == "":
        return None
    s = str(v).strip()
    if s.isdigit():
        return int(s)
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            if float(v) == int(v) and 0 < int(v) < 2**63:
                return int(v)
        except (ValueError, OverflowError):
            pass
    return None


def _vendor_id_from_comp_row(row: dict[str, Any]) -> int | None:
    """v3 /comps rows often use `id` or `propertyId` (see vendor reference)."""
    for key in ("id", "propertyId", "property_id", "priorId", "prior_id"):
        n = _int_vendor_property_id(row.get(key))
        if n is not None:
            return n
    return None


def _vendor_id_from_subject(subj: dict[str, Any]) -> int | None:
    for key in ("id", "propertyId", "property_id"):
        n = _int_vendor_property_id(subj.get(key))
        if n is not None:
            return n
    return None


def format_property_search_for_prompt(
    response: dict[str, Any] | None,
) -> tuple[str, list[int]]:
    """Return (summary text, property ids) for the model; strips heavy fields."""
    if not response or not isinstance(response, dict):
        return "", []
    st = response.get("statusCode") or response.get("status")
    if st is not None and int(str(st)) != 200:
        return "", []
    data = response.get("data")
    if not isinstance(data, list) or not data:
        return "Property search returned no records for these filters (RealEstateAPI; not a substitute for MLS).", []
    lines: list[str] = [
        "Source: RealEstateAPI PropertySearch (not MLS; verify with your MLS and material facts).",
    ]
    ids: list[int] = []
    for i, row in enumerate(data[:25], start=1):
        if not isinstance(row, dict):
            continue
        n = _int_vendor_property_id(row.get("id"))
        if n is None:
            n = _int_vendor_property_id(row.get("propertyId")) or _int_vendor_property_id(
                row.get("property_id")
            )
        if n is not None:
            ids.append(n)
        parts: list[str] = []
        for key in (
            "address",
            "city",
            "state",
            "zip",
            "beds",
            "baths",
            "livingSquareFeet",
            "mlsListingPrice",
            "mlsListPrice",
            "estimatedValue",
        ):
            if key in row and row[key] is not None and str(row[key]) != "":
                parts.append(f"{key}={row[key]}")
        lines.append(f"  {i}. " + (", ".join(parts) if parts else str(row)[:200]))
    if len(data) > 25:
        lines.append(f"  (showing 25 of {len(data)} returned rows; narrow filters for fewer results.)")
    return "\n".join(lines) if len(lines) > 1 else "", ids


def _merge_v3_comps_envelope(r: dict[str, Any]) -> dict[str, Any]:
    """Vendor v3 body often nests subject/comps under `data`; merge for one consistent view."""
    inner = r.get("data")
    if not isinstance(inner, dict):
        return r
    out = dict(r)
    for k in (
        "subject",
        "comps",
        "reapiAvm",
        "reapiAvmLow",
        "reapiAvmHigh",
        "statusMessage",
        "recordCount",
        "warning",
    ):
        if k in inner and inner.get(k) is not None:
            out[k] = inner[k]
    if inner.get("comps") is not None or inner.get("subject") is not None:
        if inner.get("statusCode") is not None:
            out["statusCode"] = inner["statusCode"]
        if inner.get("status") is not None:
            out["status"] = inner["status"]
    else:
        if out.get("statusCode") is None and inner.get("statusCode") is not None:
            out["statusCode"] = inner["statusCode"]
        if out.get("status") is None and inner.get("status") is not None:
            out["status"] = inner["status"]
    return out


def format_comps_list_for_prompt(response: dict[str, Any] | None) -> tuple[str, list[int]]:
    """Summarize v3 /PropertyComps response: comps list + subject id."""
    if not response or not isinstance(response, dict):
        return "", []
    r = _merge_v3_comps_envelope(response)
    st = r.get("statusCode") if r.get("statusCode") is not None else r.get("status")
    if st is not None and int(str(st)) != 200:
        sm = r.get("statusMessage") or r.get("message") or "error"
        return (
            f"RealEstateAPI v3 PropertyComps returned status {st} (not 200). Message: {sm!s} "
            "(Check address formatting, entitlements, or try `exact_match: false`.)",
            [],
        )
    lines: list[str] = [
        "Source: RealEstateAPI v3 PropertyComps (not MLS; verify with your MLS and material facts).",
    ]
    ids: list[int] = []
    subj = r.get("subject")
    if isinstance(subj, dict):
        sn = _vendor_id_from_subject(subj)
        if sn is not None:
            ids.append(sn)
    comps = r.get("comps")
    if isinstance(comps, list) and comps:
        for i, row in enumerate(comps[:20], start=1):
            if not isinstance(row, dict):
                continue
            cl = _comp_row_oneline(row)
            lines.append(f"  Comp {i}. {cl}")
    else:
        lines.append("  (No comparable properties returned; widen radius or time window in settings.)")
    if isinstance(r.get("reapiAvm"), (str, int, float)) or r.get("reapiAvmLow"):
        lines.append(
            f"  Vendor AVM range: {r.get('reapiAvmLow', '')!s} – {r.get('reapiAvm', '')!s} / {r.get('reapiAvmHigh', '')!s}"
        )
    if isinstance(comps, list):
        for row in comps:
            if not isinstance(row, dict):
                continue
            n = _vendor_id_from_comp_row(row)
            if n is not None:
                ids.append(n)
    if isinstance(comps, list) and len(comps) > 0 and not ids:
        k0: list[str] = []
        if comps and isinstance(comps[0], dict):
            k0 = list(comps[0].keys())[:24]
        logger.warning(
            "reapi v3 comps: %d comp rows but no extractable vendor ids (first row keys: %s)",
            len(comps),
            k0,
        )
    return "\n".join(lines) if len(lines) > 1 else "", list(dict.fromkeys(ids))


def _comp_row_oneline(row: dict[str, Any]) -> str:
    pi = row.get("propertyInfo")
    if isinstance(pi, dict):
        addr = pi.get("address")
        if isinstance(addr, dict):
            label = addr.get("label") or addr.get("address")
            if label:
                return str(label)[:200]
    # v3 comps rows often use flat `address: { "address": "…", "city", "state" }` (no propertyInfo)
    a = row.get("address")
    if isinstance(a, dict):
        line = a.get("address") or a.get("label") or a.get("street")
        if line:
            c = a.get("city")
            s = a.get("state")
            z = a.get("zip")
            tail = ", ".join(str(x) for x in (c, s, z) if x)
            return (str(line) + (f", {tail}" if tail else ""))[:200]
    parts: list[str] = []
    for k in (
        "lastSaleAmount",
        "lastSaleDate",
        "squareFeet",
        "bedrooms",
        "bathrooms",
    ):
        if k in row and row[k] is not None and str(row[k]) != "":
            parts.append(f"{k}={row[k]}")
    if parts:
        return (", ".join(parts))[:200]
    return str(row.get("id", ""))[:80]


def format_property_detail_for_prompt(response: dict[str, Any] | None) -> str:
    """Turn a PropertyDetail JSON body into a short, model-safe string for the system context."""
    if not response or not isinstance(response, dict):
        return ""

    status = response.get("statusCode") or response.get("status")
    if status is not None and int(str(status)) != 200:
        return ""

    inner = response.get("data")
    if not isinstance(inner, dict):
        return ""

    lines: list[str] = [
        "Source: RealEstateAPI public-record & aggregated data (not MLS; verify material facts).",
    ]

    pid = inner.get("id")
    if pid is not None:
        lines.append(f"Property id: {pid}")

    pi = inner.get("propertyInfo")
    if isinstance(pi, dict):
        # Never surface owner/occupant names into the model; public-record can include PII.
        pii_subkeys = frozenset(
            {
                "owner",
                "owner1Name",
                "owner2Name",
                "ownerName",
                "ownerFirstName",
                "ownerLastName",
                "mailingAddress",
            }
        )
        if any(k in pi and pi.get(k) is not None for k in pii_subkeys):
            lines.append("Owner/occupant names omitted from this summary (PII).")
        parts: list[str] = []
        addr = pi.get("address")
        if isinstance(addr, dict):
            lbl = addr.get("label") or addr.get("address")
            if lbl:
                parts.append(str(lbl))
        for key in (
            "bedrooms",
            "bathrooms",
            "yearBuilt",
            "livingSquareFeet",
            "lotSquareFeet",
        ):
            if key in pi and pi[key] is not None:
                parts.append(f"{key}={pi[key]}")
        if parts:
            lines.append("Property: " + " | ".join(parts))

    if inner.get("lastSaleDate") or inner.get("lastSalePrice"):
        lines.append(
            f"Last sale (as reported): date={inner.get('lastSaleDate', 'N/A')!s}  "
            f"price={inner.get('lastSalePrice', 'N/A')!s}"
        )

    if inner.get("estimatedValue") is not None or inner.get("reapiAvm") is not None:
        avm = inner.get("reapiAvm")
        if isinstance(avm, dict) and avm:
            lines.append(f"AVM/estimate: {avm!s}")
        elif inner.get("estimatedValue") is not None:
            lines.append(f"Estimated value: {inner.get('estimatedValue')}")

    ti = inner.get("taxInfo")
    if isinstance(ti, dict):
        ta = ti.get("taxAmount")
        ay = ti.get("assessmentYear") or ti.get("year")
        if ta is not None or ay is not None:
            lines.append(f"Tax: amount={ta!s}  year={ay!s}")

    sh = inner.get("saleHistory")
    if isinstance(sh, list) and sh:
        lines.append("Recent sale/transfer history (recorder; check transactionType):")
        for row in sh[:5]:
            if not isinstance(row, dict):
                continue
            lines.append(
                f"  - {row.get('saleDate', '?')!s}  amount={row.get('saleAmount', 'N/A')!s}  "
                f"type={row.get('transactionType', 'N/A')!s}"
            )

    msg = response.get("statusMessage") or inner.get("statusMessage")
    if msg:
        lines.append(f"API message: {msg}")
    if inner.get("live") is not None:
        lines.append(f"Data live flag: {inner.get('live')}")

    return "\n".join(lines) if len(lines) > 1 else ""


async def public_context_for_address(address_one_line: str) -> str:
    """Convenience: full round-trip to formatted string."""
    raw = await fetch_property_detail(address=address_one_line, include_comps=False)
    return format_property_detail_for_prompt(raw) if raw else ""


def pick_property_for_public_data(project: Any) -> Any | None:
    """Choose subject property for public-record context: sale_property_id when set (seller-leaning), else open tx, else first with address."""
    ct = (getattr(project, "client_type", None) or "").strip().lower()
    sale_id = getattr(project, "sale_property_id", None)
    if sale_id and ct in ("seller", "buyer & seller", "buyer and seller"):
        for pr in project.properties or ():
            if getattr(pr, "id", None) == sale_id and getattr(pr, "address", None) and str(pr.address).strip():
                return pr
    for t in project.transactions or ():
        if t.status in ("closed", "dead"):
            continue
        pr = getattr(t, "property", None)
        if pr and getattr(pr, "address", None) and str(pr.address).strip():
            return pr
    for pr in project.properties or ():
        if getattr(pr, "address", None) and str(pr.address).strip():
            return pr
    return None


async def public_context_for_project_property(project: Any) -> str:
    """Fetch and format public-record context for the best-matching linked Property, or ''."""
    prop = pick_property_for_public_data(project)
    if not prop:
        return ""
    line = build_address_one_line(
        str(prop.address or ""),
        getattr(prop, "city", None),
        getattr(prop, "state", None),
        getattr(prop, "zip_code", None),
    )
    if not line:
        return ""
    rid = getattr(prop, "reapi_property_id", None)
    raw = None
    if rid and str(rid).strip():
        raw = await fetch_property_detail(property_id=str(rid).strip(), include_comps=False)
    if not raw:
        raw = await fetch_property_detail(address=line, include_comps=False)
    text = format_property_detail_for_prompt(raw) if raw else ""
    if not text:
        return ""
    return text


def build_address_one_line(
    address: str,
    city: str | None,
    state: str | None,
    zip_code: str | None,
) -> str:
    """Single-line U.S. address for PropertyDetail (preferred when all parts exist)."""
    a = (address or "").strip()
    if not a:
        return ""
    c = (city or "").strip()
    s = (state or "MI").strip() or "MI"
    z = (str(zip_code or "")).strip()
    if c and s and z:
        return f"{a}, {c} {s} {z}"
    if c and s:
        return f"{a}, {c} {s}"
    return a
