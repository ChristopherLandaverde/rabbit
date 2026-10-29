"""FastAPI dependencies for authenticated and scoped v2 routes."""

from fastapi import Depends, Request

from .errors import ApiProblem


async def require_api_key(request: Request):
    key = getattr(request.state, "api_key", None)
    if key is None:
        raise ApiProblem(
            401,
            "missing_api_key",
            "API key required",
            "This endpoint requires an API key.",
            "Send Authorization: Bearer rk_live_… or rk_test_….",
            "https://docs.rabbit.example/authentication",
        )
    return key


def require_scope(scope: str):
    async def check_scope(key=Depends(require_api_key)):
        if not hasattr(key, "scopes"):
            return key
        if scope not in key.scopes:
            raise ApiProblem(
                403,
                "insufficient_scope",
                "Insufficient scope",
                f"This endpoint requires the {scope} scope.",
                f"Issue a key with the {scope} scope.",
                "https://docs.rabbit.example/authentication#scopes",
            )
        return key

    return check_scope
