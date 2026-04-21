"""Multi-provider LLM: allowlists, env key checks, context budgets, /api/llm/options payload."""

from __future__ import annotations

import os
from typing import Any

from config import (
    ANTHROPIC_MODEL,
    DEFAULT_LLM_PROVIDER,
    GEMINI_CHAT_MODEL,
    OPENAI_CHAT_MODEL,
    BUDGET_DOCUMENTS,
    BUDGET_EMAILS,
    BUDGET_HISTORY_MESSAGES,
    BUDGET_PROFILE,
    BUDGET_TRANSACTION,
)


def _uniq(*items: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(x for x in items if x))


MODEL_ALLOWLIST: dict[str, tuple[str, ...]] = {
    "anthropic": _uniq(ANTHROPIC_MODEL, "claude-3-5-haiku-20241022"),
    "openai": _uniq(OPENAI_CHAT_MODEL, "gpt-4o-mini", "gpt-4o", "gpt-4.1-mini"),
    "gemini": _uniq(GEMINI_CHAT_MODEL, "gemini-2.0-flash", "gemini-1.5-flash"),
}

# Approximate context window (tokens) for scaling document/email budgets vs 200k Claude.
_CONTEXT_WINDOW: dict[str, int] = {
    "anthropic": 200_000,
    "openai": 128_000,
    "gemini": 1_000_000,
}

_BASELINE_CTX = 200_000


def anthropic_api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def openai_api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "").strip()


def gemini_api_key() -> str:
    return os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()


def provider_key_configured(provider: str) -> bool:
    p = provider.lower()
    if p == "anthropic":
        return bool(anthropic_api_key())
    if p == "openai":
        return bool(openai_api_key())
    if p == "gemini":
        return bool(gemini_api_key())
    return False


def default_model(provider: str) -> str:
    p = provider.lower()
    if p == "anthropic":
        return ANTHROPIC_MODEL
    if p == "openai":
        return OPENAI_CHAT_MODEL
    if p == "gemini":
        return GEMINI_CHAT_MODEL
    return ANTHROPIC_MODEL


def resolve_llm(stored_provider: str | None, stored_model: str | None) -> tuple[str, str]:
    """Return concrete (provider, model) for a chat request."""
    raw = (stored_provider or DEFAULT_LLM_PROVIDER or "anthropic").strip().lower()
    if raw not in MODEL_ALLOWLIST:
        raw = "anthropic"
    allowed = MODEL_ALLOWLIST[raw]
    model = (stored_model or "").strip() or default_model(raw)
    if model not in allowed:
        model = default_model(raw)
    return raw, model


def missing_key_message(provider: str) -> str:
    if provider == "anthropic":
        return "ANTHROPIC_API_KEY is not set on the server."
    if provider == "openai":
        return "OPENAI_API_KEY is not set on the server."
    return "GEMINI_API_KEY or GOOGLE_API_KEY is not set on the server."


def get_context_budgets(provider: str) -> dict[str, int]:
    """Scale document/email budgets down for smaller context windows (e.g. OpenAI 128k)."""
    p = provider.lower() if provider in MODEL_ALLOWLIST else "anthropic"
    cap = _CONTEXT_WINDOW.get(p, _BASELINE_CTX)
    scale = min(1.0, cap / _BASELINE_CTX)
    return {
        "transaction": BUDGET_TRANSACTION,
        "profile": BUDGET_PROFILE,
        "documents": max(8_000, int(BUDGET_DOCUMENTS * scale)),
        "emails": max(4_000, int(BUDGET_EMAILS * scale)),
        "history_messages": BUDGET_HISTORY_MESSAGES,
    }


def list_llm_options() -> dict[str, Any]:
    labels = {
        "anthropic": "Anthropic",
        "openai": "OpenAI",
        "gemini": "Google Gemini",
    }
    providers: list[dict[str, Any]] = []
    for pid in ("anthropic", "openai", "gemini"):
        if not provider_key_configured(pid):
            continue
        models = [{"id": m, "label": m} for m in MODEL_ALLOWLIST[pid]]
        providers.append({"id": pid, "label": labels[pid], "models": models})
    dp = DEFAULT_LLM_PROVIDER if DEFAULT_LLM_PROVIDER in MODEL_ALLOWLIST else "anthropic"
    if not provider_key_configured(dp):
        dp = providers[0]["id"] if providers else dp
    return {"providers": providers, "default_provider": dp}


def model_display_name(provider: str, model: str) -> str:
    """Short label for errors / logs."""
    return f"{model} ({provider})"


# --- Tier allowlists (trial = cheap models only; pro = full MODEL_ALLOWLIST per provider) ---
TRIAL_TIER_MODELS: dict[str, tuple[str, ...]] = {
    "anthropic": _uniq("claude-3-5-haiku-20241022"),
    "openai": _uniq("gpt-4o-mini"),
    "gemini": _uniq("gemini-2.0-flash", "gemini-1.5-flash"),
}


def _pro_allow_premium_models() -> bool:
    """When False, Pro uses the same cheap allowlist as trial (strong COGS control)."""
    return os.environ.get("PRO_ALLOW_PREMIUM_MODELS", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )


def models_for_subscription_tier(tier: str, provider: str) -> tuple[str, ...]:
    p = provider.lower()
    if p not in MODEL_ALLOWLIST:
        return ()
    if (tier or "").strip().lower() == "pro":
        if _pro_allow_premium_models():
            return MODEL_ALLOWLIST[p]
        return tuple(m for m in TRIAL_TIER_MODELS.get(p, ()) if m in MODEL_ALLOWLIST[p])
    return tuple(m for m in TRIAL_TIER_MODELS.get(p, ()) if m in MODEL_ALLOWLIST[p])


def pair_allowed_for_tier(tier: str, provider: str, model: str) -> bool:
    allowed = models_for_subscription_tier(tier, provider)
    return model in allowed


def coerce_llm_for_tier(
    tier: str,
    stored_provider: str | None,
    stored_model: str | None,
) -> tuple[str, str]:
    """Resolve stored prefs then clamp to tier + configured keys."""
    p, m = resolve_llm(stored_provider, stored_model)
    tier_l = (tier or "trial").strip().lower()
    allowed_models = models_for_subscription_tier(tier_l, p)
    if m in allowed_models and provider_key_configured(p):
        return p, m
    # Pick first provider that has keys and trial/pro models
    order = ("anthropic", "openai", "gemini")
    for pid in order:
        if not provider_key_configured(pid):
            continue
        opts = models_for_subscription_tier(tier_l, pid)
        if opts:
            return pid, opts[0]
    return p, m


def normalize_project_llm_for_account(
    llm_provider: str | None,
    llm_model: str | None,
    tier: str,
) -> tuple[str | None, str | None]:
    """Persist only valid provider/model for tier and configured keys; None = use defaults at chat."""
    if not llm_provider and not llm_model:
        return None, None
    p = (llm_provider or "").strip().lower()
    if p not in MODEL_ALLOWLIST:
        return None, None
    if not provider_key_configured(p):
        return None, None
    allowed = models_for_subscription_tier(tier, p)
    m = (llm_model or "").strip() or (allowed[0] if allowed else default_model(p))
    if m not in allowed:
        m = allowed[0] if allowed else default_model(p)
    if m not in MODEL_ALLOWLIST[p]:
        m = default_model(p)
    return p, m


def list_llm_options_for_tier(tier: str) -> dict[str, Any]:
    """Same as list_llm_options but models filtered by subscription tier."""
    labels = {
        "anthropic": "Anthropic",
        "openai": "OpenAI",
        "gemini": "Google Gemini",
    }
    tier_l = (tier or "trial").strip().lower()
    providers: list[dict[str, Any]] = []
    for pid in ("anthropic", "openai", "gemini"):
        if not provider_key_configured(pid):
            continue
        allowed = models_for_subscription_tier(tier_l, pid)
        if not allowed:
            continue
        models = [{"id": m, "label": m} for m in allowed]
        providers.append({"id": pid, "label": labels[pid], "models": models})
    dp = DEFAULT_LLM_PROVIDER if DEFAULT_LLM_PROVIDER in MODEL_ALLOWLIST else "anthropic"
    if not provider_key_configured(dp) or not models_for_subscription_tier(tier_l, dp):
        dp = providers[0]["id"] if providers else dp
    return {"providers": providers, "default_provider": dp, "subscription_tier": tier_l}
