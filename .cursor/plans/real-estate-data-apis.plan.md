---
name: RealEstateAPI property data (v1)
overview: Research RealEstateAPI **key scopes/permissions** (least privilege), then wire the backend. Env `REALESTATEAPI_BACKEND` / `REALESTATEAPI_FRONTEND` as documented. Broader options in docs/real-estate-data-sources-research.md.
todos:
  - id: reapi-scopes
    content: Research RealEstateAPI docs/dashboard for API key scopes or permission sets; list endpoints needed for v1; enable only those; note any product/dashboard steps
    status: completed
  - id: reapi-integrate
    content: After scopes—wire RealEstateAPI in REMI backend (use REALESTATEAPI_BACKEND, property flow, errors, optional cache); never expose secrets to client
    status: completed
isProject: false
---

# Property data — v1 (RealEstateAPI)

## Problem statement

REMI needs **programmatic property context** for chat: things like **last recorded sale**, **tax**, **characteristics**, and **comps-style** background—e.g. *“What did 410 Elm St. sell for last time?”*

**Reality:** there is no simple public “Zillow API” or “Realtor.com API” for third-party apps, and **MLS** (e.g. **Realcomp RAPI**) is **licensed, purpose-scoped** data—not a drop-in for every user. For **v1**, we use a **public-records / aggregated** provider so we can ship without blocking on MLS contracts.

**Deeper options, Zillow/Bridge, ATTOM, Realcomp/RAPI, and A/B/C tradeoffs** are archived in [docs/real-estate-data-sources-research.md](docs/real-estate-data-sources-research.md).

---

## v1 decision


| Item         | Choice                                                                                                                                                                                                                                                                              |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Approach** | **Option B** — national **property “fast facts”** (not live MLS).                                                                                                                                                                                                                   |
| **Provider** | **[RealEstateAPI](https://developer.realestateapi.com/)** (API key already obtained; easy setup).                                                                                                                                                                                   |
| **Secrets**  | In `**.env`**: `REALESTATEAPI_BACKEND` (use this for **all server-side** property API calls) and `REALESTATEAPI_FRONTEND` (only if the vendor’s browser/client workflow requires it—**chat enrichment should not ship the backend key to the client**). **Never commit** real keys. |
| **Later**    | **Realcomp RAPI** (or other MLS) only when you want **licensed** SE MI listing/sold data; see the research doc checklist.                                                                                                                                                           |


---

## Implementation scope

### 1. API key scopes (`reapi-scopes`)

- **Research** [RealEstateAPI](https://developer.realestateapi.com/) (and your **dashboard**, if that is where keys/scopes are managed) for how **keys** map to **permissions**, **datasets**, or **scopes**—vendor wording varies.
- **Decide** which **endpoints** v1 needs (e.g. property detail, address search, comps—only what the chat will call).
- **Principle of least privilege:** turn on or request only the **scopes** needed for those calls; **document** the list in a short dev note (or a comment in config) for future key rotation and audits.

### 2. Integration (`reapi-integrate`)

- Add a **small backend client** (or service module) that calls the RealEstateAPI endpoints you need (commonly **property detail** by address or id — follow [current docs](https://developer.realestateapi.com/)).
- **Read** `REALESTATEAPI_BACKEND` from **environment**; validate presence at startup or on first use; **never** return the key in API responses.
- Map responses into whatever shape REMI’s chat / context layer expects; handle **empty match**, **rate limits**, and **$0`/`transactionType`** (non–arms-length) sensibly in prompts.
- **Optional:** short TTL **cache** by normalized address to reduce cost and repeat calls.
- **Optional validation:** a few **known SE Michigan** addresses in dev/staging to confirm **match** and **sale** fields.

---

## Reference

- [RealEstateAPI developer documentation](https://developer.realestateapi.com/)
- [Options & MLS research (archive)](../../docs/real-estate-data-sources-research.md)

