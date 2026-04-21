---
name: Trial economics and billing
overview: Product and backend work for hosted free trials (capped spend), managed inference for paid users, metering, tier gates, in-app model switching, and host-side API keys per provider. Coordinate with multi-model implementation (Decision 1). Packaging — two public tiers (Trial + Pro), heavy usage via overage or packs on Pro. Fully managed keys (no BYOK) in scope.
todos:
  - id: in-app-model-switcher
    content: Ship in-app provider/model selection (Client Settings + chat chrome) per multi-model-providers.plan.md; filter selectable models by tier-model-allowlist for trial vs Pro
    status: completed
  - id: host-api-keys
    content: Document and configure host env API keys for each integrated provider; keep .env.example in sync with backend (see Host API keys section)
    status: completed
  - id: define-trial-caps
    content: Define trial window + max messages (and/or max tokens); document worst-case COGS with chosen cheap default model
    status: completed
  - id: persist-usage
    content: Add DB fields or table for trial_messages_used / billing_period counters; enforce before LLM stream in chat route
    status: completed
  - id: tier-model-allowlist
    content: Map subscription tier → allowed providers/models; block flagship models on free trial in same validation layer
    status: completed
  - id: stripe-or-paywall
    content: Choose v1 paywall (manual upgrade link) vs Stripe subscription; defer metered overage until needed
    status: completed
  - id: optional-byok
    content: If offering BYOK for Pro/enterprise — encrypted per-account API keys and per-request routing (separate from trial caps). Defer or skip if product is fully managed-keys only.
    status: cancelled
isProject: true
---

# Trial economics, managed keys, and paid tiers (Decisions 2–3)

Multi-provider LLM wiring (Anthropic / OpenAI / Gemini) is specified in [multi-model-providers.plan.md](multi-model-providers.plan.md) (Decision 1). **This plan requires that work** for managed inference: users switch models in-app; you fund calls with **your** keys on the host.

## Context (from product discussion)

- You want a **hosted free trial** that still **hooks** users without requiring API keys up front.
- You are **concerned about fronting unlimited API spend**; you want **paid subscribers** to cover ongoing managed inference where possible.
- You selected **capped hosted trial**: you pay for trial usage, but **hard caps** (messages and/or days) plus a **cheap default model** bound maximum exposure.

## Technical surface area (when you implement)

- **Enforcement point**: before starting the chat stream (same place you will read `project.llm_provider` / `project.llm_model` today), check trial/subscription state and increment usage after success (or reserve-before-call to prevent races — decide later).
- **Data**: counters per `Account` (or per `Project`, depending on whether limits are per-user or per-workspace).
- **Product**: post-trial **paywall** and/or **BYOK** for users who prefer to pay providers directly (BYOK optional if you stay fully managed; see below).

## Fully managed keys only (no BYOK) — how pricing tiers work (Trial + Pro; Enterprise ignored)

**What changes vs BYOK:** You pay the model provider for **every** token. There is no “user brings their own key” safety valve, so **metering and caps are not optional**—they are how you stay solvent.

### Managed keys does not mean “no model choice”

A common tension: if you host all keys, do users lose the ability to pick a model—and do you have to run **several** provider APIs?

- **User-facing choice is still fine.** The model picker stays; what changes is **who pays the invoice** (you) and **which options appear** for that account. Trial can be **one default model** (simplest); Pro can expose a **subset** of models you’ve integrated, enforced by `tier-model-allowlist` before the stream starts.
- **Multiple providers is normal, not an edge case.** You maintain one routing layer (see [multi-model-providers.plan.md](multi-model-providers.plan.md)) and env keys per provider on the host. That is bounded engineering work—not unbounded per-user complexity like BYOK.
- **COGS control** comes from **tier × model** (cheap models on trial; pricier models only on Pro and/or counted against heavier token weights), not from hiding the picker entirely.

So: fully managed + user model choice is **compatible**; the “cost” is operating N integrations and metering, which you already planned under multi-model + this billing doc.

### Two customer states (ignore Enterprise)


| State                       | Role            | What they pay you                             | What you control                                                                                                                                         |
| --------------------------- | --------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Trial** (or “Free trial”) | Acquisition     | $0                                            | Hard cap on **time** (e.g. 14 days) and/or **messages** (and optionally tokens); **one cheap default model**; optional **one client / workspace** limit. |
| **Pro**                     | Ongoing revenue | Monthly subscription (and optionally overage) | **Included usage bundle**, **which models** they may select, **how many clients/workspaces**, enforcement in chat before stream.                         |


Marketing can still show two **columns** (Trial | Pro) even if “trial” is not a permanent free tier—it's the pre-paywall state.

### What to put *in* each tier (dimensions)

Use a small set of **orthogonal knobs**; don’t duplicate the same limit in two places.

1. **Usage (messages and/or tokens per billing period)** — Trial: low fixed cap. Pro: **included bundle** (your preferred shape: simple monthly price with generous included usage).
2. **Model access** — Trial: cheapest model only. Pro: broader allowlist (still not “everything unlimited” unless you model COGS that way).
3. **Product limits** — e.g. active clients per account; Trial often `1`, Pro `unlimited` or a higher cap.
4. **Overage path (when they hit the Pro bundle)** — This answers “upgrade nudge without a tier between Pro and Enterprise”:
  - **Same tier, metered overage:** Pro stays one SKU; after the included bundle, bill per 1k tokens / per message via Stripe usage records or a later true-up. The “nudge” is **add usage**, not **new plan name**.
  - **Same tier, top-up packs:** Credit packs or one-time “extra 100k tokens” purchases—still Pro.
  - **Hard stop until next period:** Simplest v1, worst UX for power users; good if COGS risk dominates.
  - **A third *named* tier** (e.g. “Team” / “Scale”) is only needed when **entitlements differ** (seats, SSO, admin, audit)—not merely because volume went up. Volume alone is usually **overage on Pro**, not a new tier.

So: **you do not have to introduce something between Pro and Enterprise** just because heavy users exceed the bundle. Handle volume with **overage or packs on Pro** unless the product genuinely needs a different *feature* set.

### Decision (confirmed): two public tiers + volume on Pro

**Locked for v1:** Stay at **two public tiers** (Trial + Pro). When users exceed the Pro included bundle, handle it with **metered overage** and/or **top-up packs** on the **same Pro SKU**—not a new “Pro+” tier for volume alone.

**Later, only if needed:** A separate **Teams** (or similar) product line if you add **different entitlements** (seats, org admin, SSO, audit)—not merely higher usage.

**Teams vs Enterprise (not the same thing here):** “Teams” in this plan is **placeholder naming** for a possible **mid-market, org-shaped** SKU (multi-seat, admin, SSO)—often self-serve or light sales. **Enterprise** is what you already imply on the landing page: **brokerage-wide**, custom terms, contact sales, security/onboarding. If both exist, Enterprise usually sits **above** Teams (or absorbs the largest orgs). You do not need to rename Enterprise to Teams.

### Implementation alignment

- Todos: `in-app-model-switcher`, `host-api-keys`, `define-trial-caps`, `persist-usage`, `tier-model-allowlist`, `stripe-or-paywall`. For Pro bundle + overage, `stripe-or-paywall` eventually includes **metered price components** or a documented manual process until automated.
- `optional-byok` becomes **optional product-wide**: skip if you commit to fully managed keys.

## In-app model switching (product)

Users must be able to **choose provider and model** per client workspace (saved on `Project`), with the chat UI showing **which model will answer** before they send a message.

- **Implementation detail** (files, API shape, `GET /api/llm/options`): follow [multi-model-providers.plan.md](multi-model-providers.plan.md) — types, `ClientSettings`, `ChatPanel` subtitle, `useChat` / server reads project.
- **Billing tie-in:** the same saved `llm_provider` / `llm_model` is validated by `**tier-model-allowlist`** immediately before streaming (trial sees only cheap/allowed models; Pro sees the broader list). Optionally **hide or disable** disallowed options in settings when you know account tier, or fail fast in the chat route with a clear message.

## Host API keys (operator — you)

You pay each vendor; keys live **only on the server** (never in the browser).

1. **Create API keys** with Anthropic, OpenAI, and/or Google (Gemini), depending on which providers you want to offer.
2. **Set environment variables** on every deployment (local `.env`, hosting dashboard, secrets manager). Match what the backend reads, typically:
  - `ANTHROPIC_API_KEY`
  - `OPENAI_API_KEY`
  - `GEMINI_API_KEY` or `GOOGLE_API_KEY` (match backend convention)
  - Optional defaults: `ANTHROPIC_MODEL`, `OPENAI_CHAT_MODEL`, `GEMINI_CHAT_MODEL`, `DEFAULT_LLM_PROVIDER`
3. `**GET /api/llm/options`** only lists providers whose keys are present — if a key is missing, that provider does not appear in the app until you add it.
4. Keep **[.env.example](.env.example)** (repo root and/or `frontend/.env.example` if documented) updated so future deploys list every variable name.
5. After adding or rotating a key, **redeploy or restart** the backend so process env picks it up.

## Out of scope here

- File-by-file UI/backend specifics not duplicated above (see multi-model plan).
- Exact Stripe price points or marketing copy.

## References in codebase (for the next agent)

- Chat entry: `[backend/routers/chat.py](backend/routers/chat.py)`
- Project fields for model preference: `llm_provider`, `llm_model` on `Project` (see multi-model migration notes)

When this work starts, link the metering module to the same chat path so every inference path is gated consistently.