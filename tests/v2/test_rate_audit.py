"""M1c live-key rate limiting and audit behavior."""

import asyncio

from sqlalchemy import select

from src.db.models import AuditLog


def test_live_key_gets_rate_headers_and_is_blocked_on_request_61(client, make_key):
    live = make_key(client)
    headers = {"Authorization": f"Bearer {live['key']}"}
    for _ in range(60):
        response = client.get("/v2/auth-check", headers=headers)
        assert response.status_code == 200
    response = client.get("/v2/auth-check", headers=headers)
    assert response.status_code == 429
    assert response.json()["code"] == "rate_limited"
    assert response.headers["X-RateLimit-Limit"] == "60"
    assert response.headers["X-RateLimit-Remaining"] == "0"
    assert 1 <= int(response.headers["Retry-After"]) <= 60


def test_test_key_bypasses_live_rate_limiter(client):
    signup = client.post("/v2/keys/signup").json()
    response = client.get("/v2/auth-check", headers={"Authorization": f"Bearer {signup['key']}"})
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "unlimited"
    assert response.headers["X-RateLimit-Remaining"] == "unlimited"
    assert response.headers["X-RateLimit-Reset"] == "0"
    assert not any(key.startswith("v2:rate:") for key in client.app.state.redis.events)


def test_redis_down_fails_open_for_live_key(client, make_key):
    live = make_key(client)
    client.app.state.redis.fail = True
    response = client.get("/v2/auth-check", headers={"Authorization": f"Bearer {live['key']}"})
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit"] == "60"


def test_audit_row_created_for_authenticated_mutation(client, make_key):
    created = make_key(client)
    response = client.post(
        "/v2/scope-check",
        headers={"Authorization": f"Bearer {created['key']}", "User-Agent": "m1-test"},
    )
    assert response.status_code == 200

    async def read_audit():
        async with client.app.state.test_session_factory() as session:
            return (await session.execute(select(AuditLog))).scalars().all()

    rows = asyncio.run(read_audit())
    assert len(rows) == 1
    assert rows[0].key_id == created["id"]
    assert rows[0].action == "POST"
    assert rows[0].user_agent == "m1-test"
