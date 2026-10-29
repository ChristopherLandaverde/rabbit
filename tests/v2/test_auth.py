"""M1a API key issuance and bearer authentication."""

from src.v2.auth.keys import generate_api_key, hash_api_key, verify_api_key


def test_key_entropy_prefix_and_argon2id_hashing():
    key = generate_api_key()
    assert key.startswith("rk_live_")
    assert len(key.removeprefix("rk_live_")) == 43
    encoded = hash_api_key(key)
    assert encoded.startswith("$argon2id$")
    assert verify_api_key(key, encoded)
    assert not verify_api_key("rk_live_wrong", encoded)


def test_admin_key_plaintext_once_and_authentication(client, make_key):
    created = make_key(client)
    assert created["key"].startswith("rk_live_")
    assert client.get("/v2/admin/keys", headers={"X-Admin-Bootstrap-Key": "bootstrap-secret"}).status_code == 200
    listed = client.get("/v2/admin/keys", headers={"X-Admin-Bootstrap-Key": "bootstrap-secret"}).json()
    assert "key" not in listed["keys"][0]
    assert listed["keys"][0]["key_prefix"].endswith("****")
    response = client.get("/v2/auth-check", headers={"Authorization": f"Bearer {created['key']}"})
    assert response.status_code == 200
    assert response.json() == {"livemode": True, "is_test": False}


def test_bearer_auth_errors_scope_and_revocation(client, make_key):
    response = client.get("/v2/auth-check")
    assert response.status_code == 401
    assert response.headers["content-type"].startswith("application/problem+json")
    assert response.json()["code"] == "missing_api_key"

    response = client.get("/v2/auth-check", headers={"Authorization": "Bearer rk_live_invalid"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_api_key"

    created = make_key(client, scopes=["analyses:write"])
    response = client.post("/v2/scope-check", headers={"Authorization": f"Bearer {created['key']}"})
    assert response.status_code == 403
    assert response.json()["code"] == "insufficient_scope"

    client.delete(f"/v2/admin/keys/{created['id']}", headers={"X-Admin-Bootstrap-Key": "bootstrap-secret"})
    response = client.get("/v2/auth-check", headers={"Authorization": f"Bearer {created['key']}"})
    assert response.status_code == 401


def test_bootstrap_key_required(client):
    response = client.post("/v2/admin/keys", json={"name": "x"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_bootstrap_key"
