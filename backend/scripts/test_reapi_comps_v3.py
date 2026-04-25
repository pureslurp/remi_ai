#!/usr/bin/env python3
"""Manual test: POST /v3/PropertyComps (RealEstateAPI).

Usage (from repo root):
  python3 backend/scripts/test_reapi_comps_v3.py
  python3 backend/scripts/test_reapi_comps_v3.py "123 Main St, Birmingham, MI 48009"

Requires REALESTATEAPI_BACKEND in the repo root .env. May consume API credits per vendor rules.
Docs: https://developer.realestateapi.com/reference/v3-comps-response-object
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
load_dotenv(_REPO_ROOT / ".env", override=True)

DEFAULT_ADDRESS = "100 S State St, Ann Arbor, MI 48104"


def _backend_key() -> str:
    return (
        os.environ.get("REALESTATEAPI_BACKEND", "").strip()
        or os.environ.get("REAL_ESTATE_API_KEY", "").strip()
    )


def main() -> int:
    key = _backend_key()
    if not key:
        print(
            "error: set REALESTATEAPI_BACKEND or REAL_ESTATE_API_KEY in .env (repo root)",
            file=sys.stderr,
        )
        return 1

    address = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ADDRESS).strip()
    body: dict = {
        "address": address,
        "max_results": 5,
        "max_radius_miles": 2.0,
        "max_days_back": 365,
        "exact_match": False,
    }

    url = os.environ.get("REALESTATEAPI_BASE_URL", "https://api.realestateapi.com").rstrip(
        "/"
    ) + "/v3/PropertyComps"
    print(f"POST {url}")
    print(f"address: {address!r}\n", flush=True)

    r = httpx.post(
        url,
        json=body,
        headers={
            "x-api-key": key,
            "content-type": "application/json",
            "accept": "application/json",
        },
        timeout=60.0,
    )
    print("HTTP", r.status_code, flush=True)
    try:
        out = r.json()
    except json.JSONDecodeError:
        print(r.text[:2000])
        return 1

    text = json.dumps(out, indent=2, default=str)
    if len(text) > 12000:
        print(text[:12000] + "\n... [truncated] ...")
    else:
        print(text)
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
