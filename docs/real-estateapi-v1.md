# RealEstateAPI — v1 scope and keys

## How “scopes” work

RealEstateAPI authenticates with **`x-api-key`** (see [Property Detail API](https://developer.realestateapi.com/reference/property-detail-api-1)). There is no OAuth scope list in the request; **which products your key can call** is determined by your **account / subscription** in the RealEstateAPI **dashboard** (e.g. Property Data vs MLS add-ons, etc.).

**Principle of least privilege (operational):**

- Use **`REALESTATEAPI_BACKEND`** only on the **server** (never in the browser or Vite bundle).
- **`REALESTATEAPI_FRONTEND`** is for vendor flows that require a **client** key, if any; REMI’s Python backend does **not** read that variable for the integration below.
- In the vendor UI, ensure the key used for the backend is entitled to at least **Property Data** / **Property Detail** (wording may vary by dashboard).

## Endpoints we use in v1

| Endpoint | Method | Purpose |
|----------|--------|--------|
| `https://api.realestateapi.com/v2/PropertyDetail` | `POST` | Public-record-style profile for a **U.S. address** (or property `id` from their search). |

v1 request body (minimal):

- `address` — full single-line address when we have it, **or**
- `house`, `street`, `city`, `state`, `zip` from the linked **Property** model
- `comps: false` — smaller response and avoids requiring comps/AVM add-ons until you need them. Set to `true` in code later if the subscription includes comps/AVM.

## v3 /PropertyComps (custom comps, optional)

- **Endpoint:** `POST /v3/PropertyComps` on the same base URL. Request body: `address` and/or `id` (property id), plus optional filters: `max_results` (1–50), `max_radius_miles`, `max_days_back`, `same_zip`, `arms_length`, etc. [Reference](https://developer.realestateapi.com/reference/v3-comps-response-object).
- **Billing:** Vendor states that **calling v3 directly** (vs getting comps only via Property Detail) may be priced per subject property (e.g. 1 credit per address)—see their dashboard and [.comps](https://developer.realestateapi.com/reference/comps) notes.
- **Code:** `fetch_property_comps_v3` in `backend/services/realestateapi_client.py`.
- **Manual test:** `python3 backend/scripts/test_reapi_comps_v3.py "123 Main St, City, ST 12345"` (loads `REALESTATEAPI_BACKEND` from repo `.env`).

## Optional: enable later

- Same **PropertyDetail** with `comps: true` and/or `id` from a prior search (uses older v2 comps path on the server).
- Other datasets (MLS, skip trace) **only** after you confirm subscription and compliance; not used in v1.
