"""M0 smoke tests: v2 router mounts under the env flag and serves /v2/health."""


def test_v2_health_returns_ok(v2_client):
    response = v2_client.get("/v2/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok", "version": "2.0.0"}


def test_v2_openapi_is_scoped_to_v2(v2_client):
    response = v2_client.get("/v2/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["version"] == "2.0.0"
    # Only v2 paths should appear
    for path in spec.get("paths", {}):
        assert path.startswith("/v2"), f"Non-v2 path leaked into v2 spec: {path}"
    # Health must be present
    assert "/v2/health" in spec["paths"]


def test_v2_disabled_returns_404(v1_only_client):
    response = v1_only_client.get("/v2/health")
    assert response.status_code == 404


def test_v1_health_still_works_with_v2_enabled(v2_client):
    """v2 must not break v1."""
    response = v2_client.get("/health")
    assert response.status_code == 200
