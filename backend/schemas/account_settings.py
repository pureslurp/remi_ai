from typing import Optional

from pydantic import BaseModel


class SystemPromptsOut(BaseModel):
    """Baked-in defaults plus optional per-user overrides (null = use default)."""

    default_buyer: str
    default_seller: str
    default_buyer_seller: str
    override_buyer: Optional[str] = None
    override_seller: Optional[str] = None
    override_buyer_seller: Optional[str] = None


class SystemPromptsUpdate(BaseModel):
    override_buyer: Optional[str] = None
    override_seller: Optional[str] = None
    override_buyer_seller: Optional[str] = None

    model_config = {"extra": "forbid"}


def normalize_override_updates(body: SystemPromptsUpdate) -> dict[str, Optional[str]]:
    """Strip empty strings to None so clearing a field removes the DB override."""

    def norm(v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = v.strip()
        return s if s else None

    out: dict[str, Optional[str]] = {}
    data = body.model_dump(exclude_unset=True)
    for k in ("override_buyer", "override_seller", "override_buyer_seller"):
        if k in data:
            out[k] = norm(data[k])
    return out
