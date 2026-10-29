"""Bootstrap-protected administrative API key management."""

import hmac
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from ...db.models import ApiKey
from ...db.session import get_session
from .errors import ApiProblem
from .keys import generate_api_key, hash_api_key

admin_router = APIRouter(prefix="/admin/keys", tags=["API keys"])


class CreateKey(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = Field(default_factory=list)
    mode: str = "live"
    rate_limit_per_minute: int | None = 60


async def require_bootstrap_key(x_admin_bootstrap_key: str | None = Header(default=None)):
    configured = os.getenv("ADMIN_BOOTSTRAP_KEY")
    if not configured:
        raise ApiProblem(
            503, "bootstrap_not_configured", "Admin bootstrap unavailable",
            "ADMIN_BOOTSTRAP_KEY is not configured.", "Configure the admin bootstrap key in the server environment.",
            "https://docs.rabbit.example/admin/key-issuance",
        )
    if not x_admin_bootstrap_key or not hmac.compare_digest(x_admin_bootstrap_key, configured):
        raise ApiProblem(
            401, "invalid_bootstrap_key", "Admin authentication required",
            "A valid admin bootstrap key is required.", "Send the configured X-Admin-Bootstrap-Key header.",
            "https://docs.rabbit.example/admin/key-issuance",
        )


def _response_key(key: ApiKey) -> dict:
    return {
        "id": key.id,
        "key_prefix": f"{key.key_prefix}****",
        "name": key.name,
        "scopes": key.scopes,
        "is_test": key.is_test,
        "livemode": not key.is_test,
        "rate_limit_per_minute": key.rate_limit_per_minute,
        "created_at": key.created_at.isoformat(),
        "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
    }


@admin_router.post("", status_code=201, dependencies=[Depends(require_bootstrap_key)])
async def create_key(payload: CreateKey, session: AsyncSession = Depends(get_session)):
    if payload.mode not in ("live", "test"):
        raise ApiProblem(422, "invalid_key_mode", "Invalid key mode", "mode must be live or test.",
                         "Set mode to live or test.", "https://docs.rabbit.example/admin/key-issuance")
    is_test = payload.mode == "test"
    plaintext = generate_api_key(is_test=is_test)
    key = ApiKey(
        id=str(ULID()), key_hash=hash_api_key(plaintext), key_prefix=plaintext[:12],
        name=payload.name, scopes=payload.scopes, rate_limit_per_minute=payload.rate_limit_per_minute,
        is_test=is_test, created_at=datetime.now(timezone.utc),
    )
    session.add(key)
    await session.commit()
    return {**_response_key(key), "key": plaintext}


@admin_router.get("", dependencies=[Depends(require_bootstrap_key)])
async def list_keys(session: AsyncSession = Depends(get_session)):
    keys = (await session.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))).scalars().all()
    return {"keys": [_response_key(key) for key in keys]}


@admin_router.delete("/{key_id}", status_code=204, dependencies=[Depends(require_bootstrap_key)])
async def revoke_key(key_id: str, session: AsyncSession = Depends(get_session)):
    key = await session.get(ApiKey, key_id)
    if key is None:
        raise ApiProblem(404, "key_not_found", "Key not found", "No API key has that id.",
                         "Check the key id and try again.", "https://docs.rabbit.example/admin/key-issuance")
    key.revoked_at = datetime.now(timezone.utc)
    await session.commit()
