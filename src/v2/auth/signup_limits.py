"""IP-based Redis sliding window for public key signup."""

import logging
import math
import time
import uuid

logger = logging.getLogger(__name__)


async def check_signup_limit(request) -> tuple[bool, int]:
    """Apply a 5/hour Redis sliding window per client IP."""
    redis = getattr(request.app.state, "redis", None)
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    key = f"v2:signup:{ip}"
    try:
        await redis.zremrangebyscore(key, "-inf", now - 3600)
        count = await redis.zcard(key)
        if count >= 5:
            earliest = await redis.zrange(key, 0, 0, withscores=True)
            wait = max(1, math.ceil(3600 - (now - earliest[0][1]))) if earliest else 3600
            return False, wait
        await redis.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
        await redis.expire(key, 3600)
        return True, 0
    except Exception as exc:
        logger.warning("Signup rate limiter unavailable: %s", exc)
        raise
