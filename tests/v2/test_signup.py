"""M1b self-serve signup behavior."""

import asyncio

from sqlalchemy import select

from src.db.models import SignupEvent


def test_signup_key_shape_optional_details_and_auth(client):
    response = client.post("/v2/keys/signup")
    assert response.status_code == 201
    body = response.json()
    assert body["key"].startswith("rk_test_")
    assert body["livemode"] is False
    assert body["rate_limit_per_minute"] is None
    assert client.get("/v2/auth-check", headers={"Authorization": f"Bearer {body['key']}"}).json() == {
        "livemode": False,
        "is_test": True,
    }

    assert client.post("/v2/keys/signup", json={"email": "not validated", "use_case": "testing"}).status_code == 201

    async def signup_events():
        async with client.app.state.test_session_factory() as session:
            return (await session.execute(select(SignupEvent))).scalars().all()

    events = asyncio.run(signup_events())
    assert events[-1].email == "not validated"
    assert events[-1].use_case == "testing"


def test_signup_limit_is_five_per_hour_per_ip(client):
    for _ in range(5):
        assert client.post("/v2/keys/signup").status_code == 201
    response = client.post("/v2/keys/signup")
    assert response.status_code == 429
    assert response.headers.get("Retry-After")
    assert response.json()["code"] == "rate_limited"
