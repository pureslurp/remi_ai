---
name: Multi-model providers
overview: Anthropic + OpenAI + Gemini behind one streaming entrypoint; per-project provider/model preference; GET /api/llm/options. Includes in-app UI and landing/marketing updates. Trial caps, metering, and in-app model switching are coordinated in trial-economics-and-billing.plan.md (host API keys documented there).
todos: []
isProject: true
---

# Multi-model providers (Decision 1)

Economics and trials: [trial-economics-and-billing.plan.md](trial-economics-and-billing.plan.md).

**Fully managed keys (no BYOK)** still uses this multi-provider design: you hold all API keys; users choose among **allowed** models per tier. The billing plan’s `tier-model-allowlist` gates requests after the same `llm_provider` / `llm_model` selection the UI already saves on `Project`.

---

## Backend (summary)

- Unified streaming entry (e.g. `services/chat_llm.py`) dispatching by `provider` + `model`.
- `Project.llm_provider` / `Project.llm_model` (nullable = server defaults from env).
- `GET /api/llm/options` — only providers whose API keys are set on the host; drives UI allowlists.
- Alembic migration (Postgres) + SQLite bootstrap `ALTER TABLE` for new columns.
- Env: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` or `GOOGLE_API_KEY`, optional `ANTHROPIC_MODEL`, `OPENAI_CHAT_MODEL`, `GEMINI_CHAT_MODEL`, `DEFAULT_LLM_PROVIDER`.

---

## In-app frontend (product UI)

These are the surfaces users touch after sign-in; they should stay consistent with whatever the API enforces.


| Area                  | File(s)                                                                                                                       | Change                                                                                                                                                                                                                                                                                                                                                                                         |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Types**             | [frontend/src/types/index.ts](frontend/src/types/index.ts)                                                                    | Extend `Project` with optional `llm_provider`, `llm_model` (string union or loose string + server validation).                                                                                                                                                                                                                                                                                 |
| **API client**        | [frontend/src/api/client.ts](frontend/src/api/client.ts)                                                                      | `getLlmOptions()` → `GET /api/llm/options` (typed response: providers + models + `default_provider`).                                                                                                                                                                                                                                                                                          |
| **Project update**    | Same                                                                                                                          | `updateProject` already sends partial `Project`; include new fields when saving model settings.                                                                                                                                                                                                                                                                                                |
| **Chat request**      | [frontend/src/hooks/useChat.ts](frontend/src/hooks/useChat.ts)                                                                | Either send nothing (server reads project row — simplest) **or** send `provider`/`model` in JSON if you want optimistic overrides; prefer **server reads project** so every message uses saved preference without duplicating state.                                                                                                                                                           |
| **Chat chrome**       | [frontend/src/components/ChatPanel.tsx](frontend/src/components/ChatPanel.tsx) + [frontend/src/App.tsx](frontend/src/App.tsx) | Pass active project (or `llm_provider` / `llm_model` + resolved labels) into `ChatPanel`. Show a **small subtitle** under “Kova Assistant” e.g. “Claude via Anthropic” / “GPT-4o mini via OpenAI” so agents know what will answer **before** they type.                                                                                                                                        |
| **Client settings**   | [frontend/src/components/ClientSettings.tsx](frontend/src/components/ClientSettings.tsx)                                      | New collapsible section **“Assistant model”** (or under existing area): load `/llm/options` on mount; **provider** `<select>` + **model** `<select>` filtered by provider; **save on change** (or explicit Save) via `updateProject`. If `providers` is empty, show copy: host must configure API keys in `.env`. When provider changes, reset model to first allowed model for that provider. |
| **Store / selection** | [frontend/src/store/appStore.ts](frontend/src/store/appStore.ts)                                                              | No change strictly required if `projects[]` is updated after `updateProject`; ensure any code that replaces `projects` preserves new fields (list endpoints must return them — backend `ProjectOut`).                                                                                                                                                                                          |


**UX notes**

- Disable or hide providers not returned by `/llm/options`.
- If the user’s saved provider loses a key server-side, chat should fail with a clear error; optional: grey out invalid combo in settings when options refresh.

---

## Landing / marketing page

File: [frontend/src/components/LandingPage.tsx](frontend/src/components/LandingPage.tsx).

Today the page is **Anthropic-only** (pricing bullets, BYOK section, footer). Multi-model work should **reframe** without over-promising (e.g. don’t imply hosted inference is unlimited if you are still BYOK).


| Block                                        | Current intent                                      | Suggested update                                                                                                                                                                                                                                                                                                                                                   |
| -------------------------------------------- | --------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `**FEATURES` constant** (~L32–56)            | No model mention                                    | Optional new card, e.g. **“Your choice of model”**: pick the provider that fits your workflow (Anthropic, OpenAI, Google Gemini) per client workspace — **only if** the product actually offers that in-app. If hosted keys differ from BYOK, keep wording honest.                                                                                                 |
| **Pricing intro** (~L250–252)                | “Bring your own Anthropic API key”                  | Broaden to **BYOK for AI providers** (or “bring your own API keys”) and list which vendors you support, **or** say “configure one or more providers on your server” for self-hosters.                                                                                                                                                                              |
| **Free / Pro bullets** (~L258–259, L281–282) | “Your own Anthropic API key” / “BYOK Anthropic”     | e.g. “Your own API keys (Anthropic, OpenAI, Gemini)” or split lines per tier if Pro gets different treatment later.                                                                                                                                                                                                                                                |
| **BYOK section** (~L317–336)                 | Single `ANTHROPIC_API_KEY` + Anthropic Console link | **Title**: still “Bring your own model key” or “Bring your own API keys”. **Body**: explain that the **host** sets env vars; enumerate `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY` / `GOOGLE_API_KEY` (match backend). **Links**: Anthropic Console, OpenAI API keys, Google AI Studio (or current Gemini key page) — all `rel="noopener noreferrer"`. |
| **Footer** (~L342–344)                       | “not affiliated with Google or Anthropic”           | Add **OpenAI** (and any other named vendor) if you name them in hero/pricing.                                                                                                                                                                                                                                                                                      |


Keep tone consistent with the rest of the landing: plain language, no hype stack, one sentence on *who pays for tokens* (still the key holder on BYOK).

---

## Verification

- Manual: set one key at a time, confirm `/api/llm/options` and settings UI match.
- Manual: switch model in Client Settings, send chat, confirm subtitle and response provider.
- `npm run build` (frontend) and backend import/compile CI parity.

