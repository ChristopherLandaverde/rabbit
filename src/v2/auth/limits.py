"""Redis sliding-window request limits for live API keys."""

import logging
import math
import time
import uuid

from ...db.models import ApiKey

logger = logging.getLogger(__name__)


async def check_request_limit(request, api_key: ApiKey) -> tuple[dict[str, str], int | None]:
    """Count a live key's requests in a 60 second Redis sliding window."""
    limit = api_key.rate_limit_per_minute or 60
    redis = getattr(request.app.state, "redis", None)
    key = f"v2:rate:{api_key.id}"
    now = time.time()
    try:
        await redis.zremrangebyscore(key, "-inf", now - 60)
        count = await redis.zcard(key)
        if count >= limit:
            earliest = await redis.zrange(key, 0, 0, withscores=True)
            wait = max(1, math.ceil(60 - (now - earliest[0][1]))) if earliest else 60
            reset = math.ceil(earliest[0][1] + 60) if earliest else math.ceil(now + wait)
            return {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset),
            }, wait
        await redis.zadd(key, {f"{now}:{uuid.uuid4().hex}": now})
        await redis.expire(key, 60)
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(max(0, limit - count - 1)),
            "X-RateLimit-Reset": str(math.ceil(now + 60)),
        }, None
    except Exception as exc:
        logger.warning("Request rate limiter unavailable; allowing request: %s", exc)
        return {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(limit),
            "X-RateLimit-Reset": str(math.ceil(now + 60)),
        }, None
