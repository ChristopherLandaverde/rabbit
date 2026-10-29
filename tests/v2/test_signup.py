"""M1b self-serve signup behavior."""

import asyncio

from sqlalchemy import select

from src.db.models import ApiKey, SignupEvent


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


def test_signup_key_can_upload_and_read_its_dataset(client, monkeypatch, tmp_path):
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    signup = client.post("/v2/keys/signup")
    assert signup.status_code == 201
    key = signup.json()["key"]
    headers = {"Authorization": f"Bearer {key}"}

    async def read_signup_key():
        async with client.app.state.test_session_factory() as session:
            return await session.get(ApiKey, signup.json()["id"])

    api_key = asyncio.run(read_signup_key())
    assert api_key.scopes == [
        "datasets:write",
        "datasets:read",
        "analyses:write",
        "analyses:read",
    ]

    uploaded = client.post(
        "/v2/datasets",
        headers=headers,
        files={
            "file": (
                "campaigns.csv",
                b"timestamp,channel,event_type,customer_id,conversion_value\n"
                b"2026-01-01T10:00:00Z,email,click,c1,0\n"
                b"2026-01-02T10:00:00Z,paid_search,conversion,c1,25\n",
                "text/csv",
            )
        },
    )
    assert uploaded.status_code == 202

    dataset_id = uploaded.json()["id"]
    fetched = client.get(f"/v2/datasets/{dataset_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == dataset_id
    assert fetched.json()["status"] == "ready"


def test_signup_limit_is_five_per_hour_per_ip(client):
    for _ in range(5):
        assert client.post("/v2/keys/signup").status_code == 201
    response = client.post("/v2/keys/signup")
    assert response.status_code == 429
    assert response.headers.get("Retry-After")
    assert response.json()["code"] == "rate_limited"
