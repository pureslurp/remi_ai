"""Rough token estimates for pre-flight quota checks (~4 characters per token)."""

from __future__ import annotations

from typing import Any


def _output_quota_multiplier() -> float:
    from config import OUTPUT_TOKEN_QUOTA_MULTIPLIER

    try:
        m = float(OUTPUT_TOKEN_QUOTA_MULTIPLIER)
    except (TypeError, ValueError):
        m = 1.0
    return max(0.0, m)


def _system_blocks_to_string(system: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in system:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n\n".join(parts) if parts else ""


def estimate_chat_input_tokens(
    system: list, history: list, user_message: str, *, extra_triage_input_tokens: int = 0
) -> int:
    """Conservative input-side estimate for the prompt we send to the provider."""
    text = _system_blocks_to_string(system)
    for m in history:
        text += "\n" + str(m.get("content", ""))
    text += "\n" + user_message
    return max(64, len(text) // 4 + int(extra_triage_input_tokens))


def estimate_chat_preflight_tokens(
    system: list,
    history: list,
    user_message: str,
    max_output_tokens: int,
    *,
    extra_triage_input_tokens: int = 0,
) -> int:
    """Worst-case *raw* tokens (input est + max output). Prefer estimate_chat_preflight_billable for caps."""
    return (
        estimate_chat_input_tokens(
            system, history, user_message, extra_triage_input_tokens=extra_triage_input_tokens
        )
        + max(0, int(max_output_tokens))
    )


def estimate_chat_preflight_billable(
    system: list,
    history: list,
    user_message: str,
    max_output_tokens: int,
    *,
    extra_triage_input_tokens: int = 0,
) -> int:
    """Worst-case billable units: input_est + (max_output × OUTPUT_TOKEN_QUOTA_MULTIPLIER)."""
    inp = estimate_chat_input_tokens(
        system, history, user_message, extra_triage_input_tokens=extra_triage_input_tokens
    )
    out_budget = max(0, int(max_output_tokens))
    return inp + int(out_budget * _output_quota_multiplier())


def raw_to_billable_units(input_tokens: int, output_tokens: int) -> int:
    """Billable units toward trial/pro caps (matches pre-flight math)."""
    inp = max(0, int(input_tokens or 0))
    out = max(0, int(output_tokens or 0))
    return inp + int(out * _output_quota_multiplier())


def estimate_context_token_breakdown(
    system: list,
    history: list,
    user_message: str,
    *,
    extra_triage_input_tokens: int = 0,
) -> dict[str, int]:
    """
    Per-bucket input token estimates (≈ chars/4) for dev / headers.
    - system: persona, profile, transactions, optional earlier-conversation summary, documents, emails
    - history: last N chat turns to the main model
    - user: current user message
    - triage_est: document + email triage (and any other pre-main-call cheap LLM) rolled into one
    - input_total_est: sum of the above (matches estimate_chat_input_tokens if split parts were concatenated)
    """
    sys_tok = max(0, len(_system_blocks_to_string(system)) // 4)
    hist_tok = 0
    for m in history:
        hist_tok += max(0, len(str(m.get("content", ""))) // 4)
    user_tok = max(1, len(user_message) // 4) if (user_message or "").strip() else 0
    triage = max(0, int(extra_triage_input_tokens))
    return {
        "system": sys_tok,
        "history": hist_tok,
        "user": user_tok,
        "triage_est": triage,
        "input_total_est": sys_tok + hist_tok + user_tok + triage,
    }
