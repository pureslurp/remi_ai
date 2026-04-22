import logging
import os
import json
import anthropic
from typing import AsyncGenerator
from starlette.requests import Request

from database import SessionLocal
from models import ChatMessage
from config import ANTHROPIC_MODEL, MAX_TOKENS

logger = logging.getLogger("reco")

_client = None


def _stream_error_message(exc: BaseException) -> str:
    """User-facing text; include underlying httpx/network cause when present."""
    base = str(exc).strip() or type(exc).__name__
    cause = getattr(exc, "__cause__", None)
    cause_s = str(cause).strip() if cause else ""
    if base == "Connection error.":
        hint = (
            "Cannot reach Anthropic's API. Check your network, VPN, and firewall; "
            "confirm https://api.anthropic.com is reachable from this Mac."
        )
        return f"{hint} ({cause_s})" if cause_s else hint
    if cause_s and cause_s not in base:
        return f"{base} ({cause_s})"
    return base


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


async def stream_chat(
    project_id: str,
    user_message: str,
    system: list,
    history: list,
    request: Request,
) -> AsyncGenerator[str, None]:
    client = get_client()
    full_response = ""

    try:
        with client.messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=MAX_TOKENS,
            system=system,
            messages=history + [{"role": "user", "content": user_message}],
        ) as stream:
            for text in stream.text_stream:
                if await request.is_disconnected():
                    break
                full_response += text
                yield f"data: {json.dumps(text)}\n\n"
    except Exception as e:
        logger.exception("Anthropic streaming failed")
        yield f"data: {json.dumps('[ERROR] ' + _stream_error_message(e))}\n\n"
        return

    # Persist assistant response in a fresh session (request db session is already closed)
    if full_response:
        db = SessionLocal()
        try:
            db.add(ChatMessage(project_id=project_id, role="assistant", content=full_response))
            db.commit()
        finally:
            db.close()

    yield "data: [DONE]\n\n"
