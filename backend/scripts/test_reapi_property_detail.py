#!/usr/bin/env python3
"""Manual test: POST /v2/PropertyDetail (RealEstateAPI).

Usage (from repo root):
  PYTHONPATH=backend python3 backend/scripts/test_reapi_property_detail.py
  PYTHONPATH=backend python3 backend/scripts/test_reapi_property_detail.py "1506 Mohawk Ave, Royal Oak, MI 48067"
  PYTHONPATH=backend python3 backend/scripts/test_reapi_property_detail.py --comps

See https://developer.realestateapi.com/reference/property-detail-api-1

Requires REALESTATEAPI_BACKEND or REAL_ESTATE_API_KEY in repo root .env.
Do not log full responses in production (PII / financials).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_REPO_ROOT / ".env", override=True)
if str(_REPO_ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "backend"))

from config import REALESTATEAPI_BASE_URL
from services.realestateapi_client import fetch_property_detail

DEFAULT_ADDRESS = "1506 Mohawk Ave, Royal Oak, MI 48067"
MAX_PRINT = 16_000
PROPERTY_DETAIL_PATH = "/v2/PropertyDetail"


def _has_backend_key() -> bool:
    return bool(
        os.environ.get("REALESTATEAPI_BACKEND", "").strip()
        or os.environ.get("REAL_ESTATE_API_KEY", "").strip()
    )


def _args() -> tuple[str, bool]:
    rest = [a for a in sys.argv[1:] if a not in ("--comps",)]
    address = (rest[0] if rest else DEFAULT_ADDRESS).strip()
    return address, "--comps" in sys.argv


async def _main() -> int:
    if not _has_backend_key():
        print(
            "error: set REALESTATEAPI_BACKEND or REAL_ESTATE_API_KEY in .env (repo root)",
            file=sys.stderr,
        )
        return 1

    address, with_comps = _args()
    print(f"POST {REALESTATEAPI_BASE_URL}{PROPERTY_DETAIL_PATH}", flush=True)
    print(
        f"body: address={address!r}  comps={with_comps!r}  (per Property Detail API)\n",
        flush=True,
    )

    raw = await fetch_property_detail(address=address, include_comps=with_comps)
    if raw is None:
        print("no JSON (key missing, network error, or non-200 — see backend logs).")
        return 1

    if isinstance(raw, dict) and raw.get("statusCode") is not None:
        print("statusCode", raw.get("statusCode"), "statusMessage", raw.get("statusMessage"))

    text = json.dumps(raw, indent=2, default=str)
    if len(text) > MAX_PRINT:
        print(text[:MAX_PRINT] + "\n... [truncated] ...")
    else:
        print(text)
    return 0 if (not isinstance(raw, dict) or int(str(raw.get("statusCode", 200))) == 200) else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
