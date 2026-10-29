"""Request-time API key lookup and Redis-backed counters."""

from sqlalchemy import select

from ...db.models import ApiKey
from ...db.session import async_session_factory
from .errors import problem
from .keys import verify_api_key

async def authenticate(request):
    authorization = request.headers.get("Authorization", "")
    scheme, _, plaintext = authorization.partition(" ")
    if scheme.lower() != "bearer" or not plaintext:
        return None, problem(
            401, "missing_api_key", "API key required", "This endpoint requires an API key.",
            "Send Authorization: Bearer rk_live_… or rk_test_….",
            "https://docs.rabbit.example/authentication",
        )
    if not plaintext.startswith(("rk_live_", "rk_test_")):
        return None, problem(
            401, "invalid_api_key", "Invalid API key", "The supplied API key is invalid or revoked.",
            "Check the key value or create a new key.", "https://docs.rabbit.example/authentication",
        )

    prefix = plaintext[:12]
    factory = getattr(request.app.state, "api_session_factory", async_session_factory)
    async with factory() as session:
        candidates = (await session.execute(select(ApiKey).where(ApiKey.key_prefix == prefix))).scalars()
        for key in candidates:
            if key.revoked_at is None and verify_api_key(plaintext, key.key_hash):
                key.is_test = bool(key.is_test)
                request.state.api_key = key
                return key, None
    return None, problem(
        401, "invalid_api_key", "Invalid API key", "The supplied API key is invalid or revoked.",
        "Check the key value or create a new key.", "https://docs.rabbit.example/authentication",
    )

