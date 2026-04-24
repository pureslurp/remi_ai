---
name: Document attachments v2 (size-aware triage)
overview: "Future enhancement: when the user @-tags documents, decide whether to skip supplemental document triage based on how much context those attachments already consume (e.g. a 30-page PA vs a one-page addendum), optionally merging triage picks when attachments are small."
todos: []
isProject: true
---

# Document attachments v2 — size-aware supplemental triage

## Why v2 exists

**v1 behavior** (see [agent_context_strategy_ba27eacf.plan.md](agent_context_strategy_ba27eacf.plan.md) and `backend/routers/chat.py`): if the user attaches one or more documents via `@`, the server **skips document LLM triage** and loads **full text** for those IDs only, then appends a **compact index** of all project documents (`build_document_index` in `backend/services/context_builder.py`).

That is intentionally simple and respects explicit user choice. It does not distinguish:

- A **large** tagged artifact (e.g. a 30-page purchase agreement) that already carries most of the answer, from  
- A **small** tagged artifact (e.g. a one-page addendum) that may **not** be enough for the question, even though the user correctly pointed at it.

v2 would make “skip triage” **not a single-doc boolean** but a **budget / sufficiency** decision: *How much of the document budget is already filled by the @-selected bodies?*

---

## Goal

When @-attachments are **already rich** (high token or page-equivalent load), **avoid** an extra cheap triage call and keep behavior predictable.

When @-attachments are **light** (few tokens, short addendum, cover sheet), **optionally** run **supplemental** document triage to propose **additional** full-text docs (union with @-set, never dropping @-set), or at least **surface uncertainty** in the product (see Open questions).

---

## Signals to use (implementation-side)

Prefer data you already have on `Document` / chunks—no new user input required:


| Signal                    | Source                                                                                              | Notes                                                            |
| ------------------------- | --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| **Packed token estimate** | Sum of `chunk.token_count` (or `len(text)//4` fallback) for @-’d docs, capped by `BUDGET_DOCUMENTS` | Best alignment with what actually goes in the prompt.            |
| **Raw document size**     | `size_bytes`, `chunk_count`                                                                         | Coarse; good for heuristics if token counts are missing.         |
| **Filename / summary**    | `short_summary`, `filename`                                                                         | For classification only; do not replace size metrics for gating. |


**Avoid** relying on “one document” vs “many documents” as the only rule; two one-pagers should behave like two small docs, not like “multi-doc = always triage.”

---

## Policy sketch (illustrative, not prescriptive)

These are **tuning knobs** for a future implementer, not fixed constants.

1. **Compute** `attached_tokens` = estimated tokens for all @-’d documents’ chunks that would be packed in order, stopping at `BUDGET_DOCUMENTS` (same ordering as `build_documents_section_by_ids`).
2. **Define a “sufficiency” floor** as a fraction of the document budget or an absolute token minimum, e.g.
  - `attached_tokens >= max(FLOOR_TOKENS, FRACTION * BUDGET_DOCUMENTS)` → **no supplemental document triage** (current v1 path).  
  - Otherwise → **run** `triage_document_ids` (or a cheaper variant) with a prompt that **must not remove** @-IDs from the final pack; triage only **suggests additions**.
3. **Merge rule**: `final_ids = unique(@ids + triage_ids)` in a stable order (e.g. @ first, then triage order), then `build_documents_section_by_ids` with the same `also_index=True` index appendix—or refine the index to label “Pinned” vs “Suggested by relevance” for disclosure.
4. **Fallbacks**: if triage fails, keep v1 behavior (only @ + index).
5. **User override (optional)**: a composer toggle **“Search other documents when I @ attach”** (default on or off is a product call) that forces merge behavior even when “sufficient,” or forces skip even when “insufficient.”

---

## Product / UX

- **Referenced items** (already persisted for assistant messages): extend or annotate so users can see **@ pinned** vs **auto-added** document IDs when v2 merge runs.  
- **No silent removal** of @-’d documents; triage may only add.

---

## Cost and entitlements

- Extra triage only when the **sufficiency** check fails, so many real turns (user @’s a full PA) still avoid the cheap call.  
- Preflight (`extra_triage_input_tokens`) and headers (`X-Context-Breakdown`) should reflect **conditional** document triage the same way as today’s email + doc triage.  
- Document **one** place that defines the sufficiency rule so support and future tuning stay clear.

---

## Open questions (for `/ce-plan` or a design pass)

- **Thresholds:** fixed constants vs per–subscription tier vs env (`ATTACH_SUFFICIENCY_PCT`)?  
- **Triage scope when merging:** should triage see the **full** doc index, or an index **excluding** @-docs to reduce duplicate picks? (Excluding reduces noise; including may help “related” names.)  
- **Small doc, big question:** token sufficiency may still miss nuance; optional **“answer may be incomplete”** nudge in UI when below threshold and user declines the toggle.  
- **Relationship to RAG** (if ever): size-aware gating and merge rules should stay compatible with a future retrieval layer; avoid baking in “triage is the only add.”

---

## Suggested phasing

1. **Metrics only (no behavior change):** log `attached_tokens` vs `BUDGET_DOCUMENTS` on @ requests in dev/staging to see distribution.
2. **Feature flag:** `ATTACHMENT_SUPPLEMENTAL_TRIAGE=0|1` with conservative thresholds.
3. **UI + disclosure** once merge behavior is stable.
4. Revisit **defaults** after real usage; pair with A/B or internal dogfood.

---

## References in repo

- Chat branching: `backend/routers/chat.py` (attachments → `build_documents_section_by_ids`, `elif` triage path).  
- Section builder: `build_documents_section_by_ids`, `build_document_index` in `backend/services/context_builder.py`.  
- Triage: `backend/services/context_triage.py` (`triage_document_ids`).  
- Budgets: `BUDGET_DOCUMENTS`, `BUDGET_HISTORY_MESSAGES` in `backend/config.py`.

This file is a **roadmap** only; it does not change production behavior until implemented.