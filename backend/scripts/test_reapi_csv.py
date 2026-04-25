#!/usr/bin/env python3
"""Manual test: POST /v2/CSVBuilder (RealEstateAPI).

Usage (from repo root):
  python3 backend/scripts/test_reapi_csv.py 197185040
  python3 backend/scripts/test_reapi_csv.py 197185040 197185041

Requires REALESTATEAPI_BACKEND in repo root .env.
See https://developer.realestateapi.com/reference/csv-generator-api
Each `map` entry must be at least 3 characters (e.g. use `propertyId`, not `id`).
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

DEFAULT_MAP = [
    "propertyId",
    "address",
    "city",
    "state",
    "zip",
    "beds",
    "baths",
    "lastSaleDate",
    "lastSalePrice",
    "estimatedValue",
]


def _key() -> str:
    return (
        os.environ.get("REALESTATEAPI_BACKEND", "").strip()
        or os.environ.get("REAL_ESTATE_API_KEY", "").strip()
    )


def main() -> int:
    k = _key()
    if not k:
        print("error: set REALESTATEAPI_BACKEND or REAL_ESTATE_API_KEY in .env", file=sys.stderr)
        return 1
    ids: list[int] = []
    for a in sys.argv[1:]:
        try:
            ids.append(int(a))
        except ValueError:
            print(f"error: not an integer id: {a!r}", file=sys.stderr)
            return 1
    if not ids:
        print("usage: python3 backend/scripts/test_reapi_csv.py <int_id> [int_id ...]", file=sys.stderr)
        return 1

    base = os.environ.get("REALESTATEAPI_BASE_URL", "https://api.realestateapi.com").rstrip("/")
    url = f"{base}/v2/CSVBuilder"
    body = {
        "file_name": "reco-csv-smoke-test",
        "map": DEFAULT_MAP,
        "ids": ids,
    }
    print("POST", url, flush=True)
    print("body keys:", list(body.keys()), "ids:", ids, flush=True)
    r = httpx.post(
        url,
        json=body,
        headers={"x-api-key": k, "content-type": "application/json", "accept": "application/json"},
        timeout=90.0,
    )
    print("HTTP", r.status_code, flush=True)
    try:
        out = r.json()
    except json.JSONDecodeError:
        print(r.text[:2000])
        return 1
    print(json.dumps(out, indent=2)[:8000])
    return 0 if r.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
