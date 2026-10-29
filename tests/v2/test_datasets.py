"""Dataset upload, background validation, and lifecycle behavior."""

import asyncio

import pandas as pd
from src.db.models import Dataset


def _upload(client, api_key, filename="campaigns.csv", content=None):
    content = (
        content
        or b"timestamp,channel,event_type,customer_id,conversion_value\n2026-01-01T10:00:00Z,email,click,c1,0\n2026-01-02T10:00:00Z,paid_search,conversion,c1,25\n"
    )
    return client.post(
        "/v2/datasets",
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": (filename, content, "text/csv")},
    )


def test_upload_validates_csv_and_returns_typed_report(
    client, make_key, monkeypatch, tmp_path
):
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    key = make_key(client, scopes=["datasets:write", "datasets:read"])

    uploaded = _upload(client, key["key"])

    assert uploaded.status_code == 202
    assert uploaded.json()["status"] == "validating"
    dataset_id = uploaded.json()["id"]
    fetched = client.get(
        f"/v2/datasets/{dataset_id}", headers={"Authorization": f"Bearer {key['key']}"}
    )
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["status"] == "ready"
    assert body["touchpoint_count"] == 2
    assert body["unique_customers"] == 1
    assert body["schema_fingerprint"].startswith("sha256:")
    assert body["validation"] == {"errors": [], "warnings": []}
    assert (tmp_path / key["id"] / f"{dataset_id}.csv").exists()


def test_invalid_upload_is_saved_with_stable_typed_errors(
    client, make_key, monkeypatch, tmp_path
):
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    key = make_key(client, scopes=["datasets:write", "datasets:read"])
    uploaded = _upload(client, key["key"], content=b"channel,event_type\nemail,click\n")
    assert uploaded.status_code == 202

    body = client.get(
        f"/v2/datasets/{uploaded.json()['id']}",
        headers={"Authorization": f"Bearer {key['key']}"},
    ).json()
    assert body["status"] == "invalid"
    assert {issue["code"] for issue in body["validation"]["errors"]} == {
        "missing_required_column"
    }
    assert all(
        "row" in issue and "column" in issue and issue["code"]
        for issue in body["validation"]["errors"]
    )


def test_dataset_list_cursor_paginates_and_delete_soft_deletes(
    client, make_key, monkeypatch, tmp_path
):
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    key = make_key(
        client, scopes=["datasets:write", "datasets:read", "datasets:delete"]
    )
    headers = {"Authorization": f"Bearer {key['key']}"}
    ids = [_upload(client, key["key"]).json()["id"] for _ in range(3)]

    first = client.get("/v2/datasets?limit=2", headers=headers).json()
    assert len(first["data"]) == 2
    assert first["has_more"] is True
    second = client.get(
        f"/v2/datasets?limit=2&cursor={first['next_cursor']}", headers=headers
    ).json()
    assert len(second["data"]) == 1
    assert second["has_more"] is False

    deleted = client.delete(f"/v2/datasets/{ids[0]}", headers=headers)
    assert deleted.status_code == 204
    assert client.get(f"/v2/datasets/{ids[0]}", headers=headers).status_code == 404
    assert client.get("/v2/datasets", headers=headers).json()["data"]

    async def read_deleted():
        async with client.app.state.test_session_factory() as session:
            return await session.get(Dataset, ids[0])

    assert asyncio.run(read_deleted()).deleted_at is not None
    assert (tmp_path / key["id"] / f"{ids[0]}.csv").exists()


def test_dataset_routes_enforce_scope_and_test_live_isolation(client, make_key):
    writer = make_key(client, scopes=["datasets:write", "datasets:read"], mode="test")
    live = make_key(client, scopes=["datasets:read"], mode="live")
    write_only = make_key(client, scopes=["datasets:write"], mode="live")
    assert _upload(client, write_only["key"]).status_code == 202

    response = client.get(
        "/v2/datasets", headers={"Authorization": f"Bearer {writer['key']}"}
    )
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert (
        client.get(
            "/v2/datasets", headers={"Authorization": f"Bearer {live['key']}"}
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/v2/datasets",
            headers={"Authorization": f"Bearer {live['key']}"},
            files={"file": ("x.csv", b"", "text/csv")},
        ).status_code
        == 403
    )
    created = _upload(client, writer["key"]).json()
    assert (
        client.get(
            f"/v2/datasets/{created['id']}",
            headers={"Authorization": f"Bearer {live['key']}"},
        ).status_code
        == 404
    )


def test_upload_rejects_file_over_app_limit(client, make_key, monkeypatch):
    import src.v2.datasets as dataset_routes

    monkeypatch.setattr(dataset_routes, "MAX_FILE_SIZE_BYTES", 10)
    key = make_key(client, scopes=["datasets:write"])
    response = _upload(client, key["key"], content=b"x" * 11)
    assert response.status_code == 413
