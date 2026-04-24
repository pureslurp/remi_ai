"""Multi-provider streaming chat: Anthropic Messages, OpenAI Chat Completions, Gemini generate_content."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncGenerator

import anthropic
from starlette.requests import Request

from config import MAX_TOKENS
from database import SessionLocal
from models import ChatMessage
from services.chat_token_estimate import estimate_chat_input_tokens, raw_to_billable_units
from services.llm_config import (
    anthropic_api_key,
    gemini_api_key,
    openai_api_key,
)

logger = logging.getLogger("reco")

_anthropic_client: anthropic.Anthropic | None = None


def _stream_error_message(exc: BaseException, provider: str) -> str:
    base = str(exc).strip() or type(exc).__name__
    cause = getattr(exc, "__cause__", None)
    cause_s = str(cause).strip() if cause else ""
    if base == "Connection error." and provider == "anthropic":
        hint = (
            "Cannot reach Anthropic's API. Check your network, VPN, and firewall; "
            "confirm https://api.anthropic.com is reachable."
        )
        return f"{hint} ({cause_s})" if cause_s else hint
    if cause_s and cause_s not in base:
        return f"{base} ({cause_s})"
    return base


def _get_anthropic() -> anthropic.Anthropic:
    global _anthropic_client
    if _anthropic_client is None:
        _anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key())
    return _anthropic_client


def _system_blocks_to_string(system: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for block in system:
        if isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
    return "\n\n".join(parts) if parts else ""


def _fill_usage_fallback(
    usage_out: dict[str, int],
    system: list,
    history: list,
    user_message: str,
    full_response: str,
) -> None:
    """If the provider did not report usage, approximate (still bills the user fairly for COGS tracking)."""
    inp = int(usage_out.get("input_tokens", 0) or 0)
    out = int(usage_out.get("output_tokens", 0) or 0)
    if inp <= 0:
        usage_out["input_tokens"] = estimate_chat_input_tokens(system, history, user_message)
    if out <= 0 and full_response:
        usage_out["output_tokens"] = max(1, len(full_response) // 4)


async def stream_chat(
    project_id: str,
    user_message: str,
    system: list,
    history: list,
    request: Request,
    provider: str,
    model: str,
    usage_out: dict[str, int] | None = None,
    assistant_referenced: dict[str, Any] | None = None,
    *,
    attach_admin_usage: bool = False,
) -> AsyncGenerator[str, None]:
    if provider == "anthropic":
        async for chunk in _stream_anthropic(
            project_id,
            user_message,
            system,
            history,
            request,
            model,
            usage_out,
            assistant_referenced,
            attach_admin_usage=attach_admin_usage,
        ):
            yield chunk
    elif provider == "openai":
        async for chunk in _stream_openai(
            project_id,
            user_message,
            system,
            history,
            request,
            model,
            usage_out,
            assistant_referenced,
            attach_admin_usage=attach_admin_usage,
        ):
            yield chunk
    elif provider == "gemini":
        async for chunk in _stream_gemini(
            project_id,
            user_message,
            system,
            history,
            request,
            model,
            usage_out,
            assistant_referenced,
            attach_admin_usage=attach_admin_usage,
        ):
            yield chunk
    else:
        yield f"data: {json.dumps('[ERROR] Unknown provider')}\n\n"
        yield "data: [DONE]\n\n"


def _persist_assistant(
    project_id: str,
    full_response: str,
    referenced_items: dict[str, Any] | None = None,
    *,
    usage_for_admin: dict[str, int] | None = None,
) -> None:
    if not full_response:
        return
    ref_out: dict[str, Any] | None = None
    if referenced_items is not None:
        ref_out = dict(referenced_items)
    elif usage_for_admin is not None:
        ref_out = {}
    if usage_for_admin is not None and ref_out is not None:
        inp = max(0, int(usage_for_admin.get("input_tokens", 0) or 0))
        out = max(0, int(usage_for_admin.get("output_tokens", 0) or 0))
        ref_out["admin_usage"] = {
            "input_tokens": inp,
            "output_tokens": out,
            "billable_units": raw_to_billable_units(inp, out),
        }
    db = SessionLocal()
    try:
        db.add(
            ChatMessage(
                project_id=project_id,
                role="assistant",
                content=full_response,
                referenced_items=ref_out,
            )
        )
        db.commit()
    finally:
        db.close()


async def _stream_anthropic(
    project_id: str,
    user_message: str,
    system: list,
    history: list,
    request: Request,
    model: str,
    usage_out: dict[str, int] | None,
    assistant_referenced: dict[str, Any] | None = None,
    *,
    attach_admin_usage: bool = False,
) -> AsyncGenerator[str, None]:
    full_response = ""
    uo = usage_out if usage_out is not None else {}
    try:
        client = _get_anthropic()
        with client.messages.stream(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=history + [{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                if await request.is_disconnected():
                    break
                full_response += text
                yield f"data: {json.dumps(text)}\n\n"
            try:
                final = stream.get_final_message()
                if final and getattr(final, "usage", None):
                    uo["input_tokens"] = int(final.usage.input_tokens)
                    uo["output_tokens"] = int(final.usage.output_tokens)
            except Exception:
                logger.debug("Anthropic final usage unavailable", exc_info=True)
    except Exception as e:
        logger.exception("Anthropic streaming failed")
        yield f"data: {json.dumps('[ERROR] ' + _stream_error_message(e, 'anthropic'))}\n\n"
        yield "data: [DONE]\n\n"
        return

    _fill_usage_fallback(uo, system, history, user_message, full_response)
    _persist_assistant(
        project_id,
        full_response,
        assistant_referenced,
        usage_for_admin=uo if attach_admin_usage else None,
    )
    yield "data: [DONE]\n\n"


async def _stream_openai(
    project_id: str,
    user_message: str,
    system: list,
    history: list,
    request: Request,
    model: str,
    usage_out: dict[str, int] | None,
    assistant_referenced: dict[str, Any] | None = None,
    *,
    attach_admin_usage: bool = False,
) -> AsyncGenerator[str, None]:
    from openai import OpenAI

    full_response = ""
    uo = usage_out if usage_out is not None else {}
    system_str = _system_blocks_to_string(system)
    messages: list[dict[str, str]] = [{"role": "system", "content": system_str}]
    for m in history:
        role = m.get("role", "user")
        if role not in ("user", "assistant"):
            role = "user"
        messages.append({"role": role, "content": str(m.get("content", ""))})
    messages.append({"role": "user", "content": user_message})

    try:
        client = OpenAI(api_key=openai_api_key())
        try:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=MAX_TOKENS,
                stream=True,
                stream_options={"include_usage": True},
            )
        except TypeError:
            stream = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=MAX_TOKENS,
                stream=True,
            )
        for chunk in stream:
            if await request.is_disconnected():
                break
            if getattr(chunk, "usage", None):
                uo["input_tokens"] = int(chunk.usage.prompt_tokens)
                uo["output_tokens"] = int(chunk.usage.completion_tokens)
            ch = chunk.choices
            if not ch:
                continue
            delta = ch[0].delta
            piece = (delta.content or "") if delta else ""
            if piece:
                full_response += piece
                yield f"data: {json.dumps(piece)}\n\n"
    except Exception as e:
        logger.exception("OpenAI streaming failed")
        yield f"data: {json.dumps('[ERROR] ' + _stream_error_message(e, 'openai'))}\n\n"
        yield "data: [DONE]\n\n"
        return

    _fill_usage_fallback(uo, system, history, user_message, full_response)
    _persist_assistant(
        project_id,
        full_response,
        assistant_referenced,
        usage_for_admin=uo if attach_admin_usage else None,
    )
    yield "data: [DONE]\n\n"


async def _stream_gemini(
    project_id: str,
    user_message: str,
    system: list,
    history: list,
    request: Request,
    model: str,
    usage_out: dict[str, int] | None,
    assistant_referenced: dict[str, Any] | None = None,
    *,
    attach_admin_usage: bool = False,
) -> AsyncGenerator[str, None]:
    from google import genai
    from google.genai import types

    full_response = ""
    uo = usage_out if usage_out is not None else {}
    system_str = _system_blocks_to_string(system)
    contents: list[Any] = []
    for m in history:
        role = "user" if m.get("role") == "user" else "model"
        text = str(m.get("content", ""))
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=text)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    try:
        client = genai.Client(api_key=gemini_api_key())
        stream_it = await client.aio.models.generate_content_stream(
            model=model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_str or None,
                max_output_tokens=MAX_TOKENS,
            ),
        )
        async for chunk in stream_it:
            if await request.is_disconnected():
                break
            um = getattr(chunk, "usage_metadata", None)
            if um is not None:
                pt = getattr(um, "prompt_token_count", None)
                ct = getattr(um, "candidates_token_count", None)
                if pt is not None:
                    uo["input_tokens"] = int(pt)
                if ct is not None:
                    uo["output_tokens"] = int(ct)
            text = getattr(chunk, "text", None) or ""
            if text:
                full_response += text
                yield f"data: {json.dumps(text)}\n\n"
    except Exception as e:
        logger.exception("Gemini streaming failed")
        yield f"data: {json.dumps('[ERROR] ' + _stream_error_message(e, 'gemini'))}\n\n"
        yield "data: [DONE]\n\n"
        return

    _fill_usage_fallback(uo, system, history, user_message, full_response)
    _persist_assistant(
        project_id,
        full_response,
        assistant_referenced,
        usage_for_admin=uo if attach_admin_usage else None,
    )
    yield "data: [DONE]\n\n"
