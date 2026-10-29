"""Public self-serve test-key signup."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import ULID

from ...db.models import ApiKey, SignupEvent
from ...db.session import get_session
from .errors import problem
from .keys import generate_api_key, hash_api_key
from .signup_limits import check_signup_limit

signup_router = APIRouter(tags=["API keys"])


class SignupDetails(BaseModel):
    email: str | None = None
    use_case: str | None = None


@signup_router.post("/keys/signup", status_code=201)
async def signup(request: Request, details: SignupDetails | None = None, session: AsyncSession = Depends(get_session)):
    try:
        allowed, retry_after = await check_signup_limit(request)
    except Exception:
        return problem(503, "signup_limiter_unavailable", "Signup temporarily unavailable",
                       "Signup rate limiting is unavailable.", "Retry in a moment.",
                       "https://docs.rabbit.example/authentication#signup")
    if not allowed:
        response = problem(429, "rate_limited", "Rate limit exceeded", "Signup is limited to 5 keys per hour per IP.",
                           "Wait before requesting another key.", "https://docs.rabbit.example/authentication#signup")
        response.headers["Retry-After"] = str(retry_after)
        return response
    plaintext = generate_api_key(is_test=True)
    now = datetime.now(timezone.utc)
    key = ApiKey(
        id=str(ULID()), key_hash=hash_api_key(plaintext), key_prefix=plaintext[:12],
        name=(details.email if details and details.email else "self-serve test key"),
        scopes=["datasets:write", "datasets:read", "analyses:write", "analyses:read"],
        rate_limit_per_minute=None,
        is_test=True, created_at=now,
    )
    session.add(key)
    await session.commit()
    session.add(SignupEvent(
        id=str(ULID()), key_id=key.id,
        email=details.email if details else None,
        use_case=details.use_case if details else None,
        created_at=now,
    ))
    await session.commit()
    return {
        "id": key.id,
        "key": plaintext,
        "livemode": False,
        "rate_limit_per_minute": None,
        "created_at": key.created_at.isoformat(),
    }
