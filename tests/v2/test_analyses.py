"""Single-model async analysis: submit, poll, and read results (#16)."""

import asyncio
import time
from pathlib import Path

import pytest

from src.db.models import Dataset

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "examples" / "sample_campaigns.csv"
ALL_SCOPES = ["datasets:write", "datasets:read", "analyses:write", "analyses:read"]


def _headers(key):
    return {"Authorization": f"Bearer {key['key']}"}


def _upload(client, key, content=None, filename="campaigns.csv"):
    content = content if content is not None else SAMPLE.read_bytes()
    response = client.post(
        "/v2/datasets",
        headers=_headers(key),
        files={"file": (filename, content, "text/csv")},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def _v1_credits(client, content, model, **params):
    """Run the same file through the v1 endpoint, the reference implementation."""
    response = client.post(
        "/attribution/analyze",
        files={"file": ("data.csv", content, "text/csv")},
        data={"model_type": model, **{k: str(v) for k, v in params.items()}},
    )
    assert response.status_code == 200, response.text
    return response.json()["results"]


@pytest.fixture
def storage_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def deferred_worker(client):
    """Stop POST from draining the queue so tests can drive the worker by hand."""
    client.app.state.analysis_inline_worker = False
    yield
    client.app.state.analysis_inline_worker = True


def _set_dataset(client, dataset_id, **fields):
    async def update():
        async with client.app.state.test_session_factory() as session:
            dataset = await session.get(Dataset, dataset_id)
            for name, value in fields.items():
                setattr(dataset, name, value)
            await session.commit()

    asyncio.run(update())


@pytest.mark.parametrize(
    "model,options,v1_params",
    [
        ("linear", None, {}),
        ("first_touch", None, {}),
        ("last_touch", None, {}),
        ("time_decay", {"time_decay_half_life_days": 0.5}, {"half_life_days": 0.5}),
        (
            "position_based",
            {"position_based_weights": {"first": 0.3, "last": 0.5}},
            {"first_touch_weight": 0.3, "last_touch_weight": 0.5},
        ),
    ],
)
def test_end_to_end_sample_dataset_credits_match_v1(
    client, make_key, storage_dir, model, options, v1_params
):
    """API key -> upload sample -> validate -> analyze -> result equals v1 output."""
    key = make_key(client, scopes=ALL_SCOPES, mode="test")
    dataset_id = _upload(client, key)
    dataset = client.get(f"/v2/datasets/{dataset_id}", headers=_headers(key)).json()
    assert dataset["status"] == "ready"

    body = {"dataset_id": dataset_id, "models": [model]}
    if options:
        body["options"] = options
    submitted = client.post("/v2/analyses", headers=_headers(key), json=body)
    assert submitted.status_code == 202, submitted.text
    created = submitted.json()
    assert created["status"] == "queued"
    assert created["models"] == [model]
    assert created["livemode"] is False

    result = client.get(f"/v2/analyses/{created['id']}", headers=_headers(key))
    assert result.status_code == 200
    analysis = result.json()
    assert analysis["status"] == "succeeded", analysis
    assert analysis["started_at"] and analysis["completed_at"]
    assert analysis["progress"] == {"models_completed": 1, "models_total": 1}

    model_result = analysis["results"][model]
    assert model_result["model"] == model
    expected = _v1_credits(client, SAMPLE.read_bytes(), model, **v1_params)
    v2_channels = model_result["channels"]
    v1_channels = expected["channel_attributions"]
    assert v1_channels and set(v2_channels) == set(v1_channels)
    for channel, v1 in v1_channels.items():
        assert v2_channels[channel]["credit"] == v1["credit"]
        assert v2_channels[channel]["conversions"] == v1["conversions"]
        assert v2_channels[channel]["revenue"] == v1["revenue"]
    assert analysis["summary"]["total_conversions"] == expected["total_conversions"]
    assert analysis["summary"]["total_revenue"] == expected["total_revenue"]
    assert sum(c["credit"] for c in v2_channels.values()) == pytest.approx(1.0)


def test_result_names_model_parameters_and_states_association_not_causation(
    client, make_key, storage_dir
):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)

    defaults = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["position_based"]},
    ).json()
    tuned = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={
            "dataset_id": dataset_id,
            "models": ["time_decay"],
            "options": {"time_decay_half_life_days": 3},
        },
    ).json()

    first = client.get(f"/v2/analyses/{defaults['id']}", headers=_headers(key)).json()
    assert first["results"]["position_based"]["parameters"] == {
        "first_touch_weight": 0.4,
        "last_touch_weight": 0.4,
        "middle_touch_weight": pytest.approx(0.2),
    }
    second = client.get(f"/v2/analyses/{tuned['id']}", headers=_headers(key)).json()
    assert second["results"]["time_decay"]["parameters"] == {"half_life_days": 3.0}

    interpretation = second["interpretation"]
    assert interpretation["type"] == "association"
    statement = interpretation["statement"].lower()
    assert "time_decay" in statement or "named model" in statement
    assert "not" in statement and "causal" in statement
    assert "impact" not in str(second["results"]).lower()

    docs = client.get("/v2/openapi.json", headers=_headers(key)).json()
    post_doc = docs["paths"]["/v2/analyses"]["post"]["description"].lower()
    assert "association" in post_doc and "not causal" in post_doc


def test_dataset_not_ready_returns_409(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    _set_dataset(client, dataset_id, status="validating")

    response = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "dataset_not_ready"

    invalid = _upload(client, key, content=b"channel,event_type\nemail,click\n")
    response = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": invalid, "models": ["linear"]},
    )
    assert response.status_code == 409
    assert response.json()["code"] == "dataset_not_ready"


def test_touchpoint_cap_returns_413(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    _set_dataset(client, dataset_id, touchpoint_count=250_001)

    response = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "dataset_too_large"

    _set_dataset(client, dataset_id, touchpoint_count=250_000)
    response = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    )
    assert response.status_code == 202


@pytest.mark.parametrize(
    "body,code",
    [
        ({"models": []}, "validation_failed"),
        ({"models": ["markov"]}, "unknown_model"),
        ({"models": ["linear", "first_touch"]}, "too_many_models"),
        ({"models": ["linear"], "options": {"time_decay_half_life_days": 0}}, "validation_failed"),
        ({"models": ["position_based"], "options": {"position_based_weights": {"first": 0.7, "last": 0.6}}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": 30}}, "validation_failed"),
    ],
)
def test_rejects_invalid_model_requests(client, make_key, storage_dir, body, code):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    response = client.post(
        "/v2/analyses", headers=_headers(key), json={"dataset_id": dataset_id, **body}
    )
    assert response.status_code == 422, response.text
    assert response.json()["code"] == code


def test_status_transitions_queued_running_succeeded(
    client, make_key, storage_dir, deferred_worker
):
    from src.v2.analyses import claim_next_analysis, execute_analysis

    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    created = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    ).json()
    url = f"/v2/analyses/{created['id']}"
    factory = client.app.state.test_session_factory

    queued = client.get(url, headers=_headers(key)).json()
    assert queued["status"] == "queued"
    assert queued["results"] is None

    claimed = asyncio.run(claim_next_analysis(factory))
    assert claimed == created["id"]
    running = client.get(url, headers=_headers(key)).json()
    assert running["status"] == "running"
    assert running["progress"] == {"models_completed": 0, "models_total": 1}
    assert running["started_at"] is not None
    assert asyncio.run(claim_next_analysis(factory)) is None

    from src.v2.datasets import get_storage

    asyncio.run(execute_analysis(claimed, factory, get_storage()))
    done = client.get(url, headers=_headers(key)).json()
    assert done["status"] == "succeeded"
    assert done["progress"] == {"models_completed": 1, "models_total": 1}

    async def heartbeat():
        from src.db.models import Analysis

        async with factory() as session:
            return (await session.get(Analysis, claimed)).last_progress_at

    assert asyncio.run(heartbeat()) is not None


def test_worker_failure_marks_analysis_failed(
    client, make_key, storage_dir, deferred_worker, monkeypatch
):
    from src.v2 import analyses

    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    created = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    ).json()

    def explode(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(analyses, "compute_model_result", explode)
    from src.v2.datasets import get_storage

    processed = asyncio.run(
        analyses.process_queued_analyses(client.app.state.test_session_factory, get_storage())
    )
    assert processed == 1
    failed = client.get(f"/v2/analyses/{created['id']}", headers=_headers(key)).json()
    assert failed["status"] == "failed"
    assert failed["error"]["code"] == "analysis_failed"
    assert failed["results"] is None


def test_worker_loop_drains_queue_and_stops(
    client, make_key, storage_dir, deferred_worker
):
    from src.v2.analyses import run_worker
    from src.v2.datasets import get_storage

    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    for model in ("linear", "last_touch"):
        response = client.post(
            "/v2/analyses",
            headers=_headers(key),
            json={"dataset_id": dataset_id, "models": [model]},
        )
        assert response.status_code == 202
    queued = client.get("/v2/analyses?status=queued", headers=_headers(key)).json()
    assert len(queued["data"]) == 2

    async def drive():
        stop = asyncio.Event()
        worker = asyncio.create_task(
            run_worker(client.app.state.test_session_factory, get_storage(), 0.01, stop)
        )
        await asyncio.sleep(0.5)
        stop.set()
        await asyncio.wait_for(worker, timeout=5)

    asyncio.run(drive())
    done = client.get("/v2/analyses?status=succeeded", headers=_headers(key)).json()
    assert len(done["data"]) == 2


def test_list_filters_and_cursor_pagination(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    first_ds = _upload(client, key)
    second_ds = _upload(client, key)
    ids = []
    for dataset_id in (first_ds, first_ds, second_ds):
        response = client.post(
            "/v2/analyses",
            headers=_headers(key),
            json={"dataset_id": dataset_id, "models": ["linear"]},
        )
        ids.append(response.json()["id"])

    page = client.get("/v2/analyses?limit=2", headers=_headers(key)).json()
    assert len(page["data"]) == 2 and page["has_more"] is True
    rest = client.get(
        f"/v2/analyses?limit=2&cursor={page['next_cursor']}", headers=_headers(key)
    ).json()
    assert len(rest["data"]) == 1 and rest["has_more"] is False
    assert {a["id"] for a in page["data"] + rest["data"]} == set(ids)

    by_dataset = client.get(
        f"/v2/analyses?dataset_id={first_ds}", headers=_headers(key)
    ).json()
    assert {a["id"] for a in by_dataset["data"]} == set(ids[:2])
    assert "results" not in by_dataset["data"][0]

    succeeded = client.get("/v2/analyses?status=succeeded", headers=_headers(key)).json()
    assert len(succeeded["data"]) == 3
    assert client.get("/v2/analyses?status=queued", headers=_headers(key)).json()["data"] == []
    bad = client.get("/v2/analyses?status=done", headers=_headers(key))
    assert bad.status_code == 422


def test_test_and_live_keys_cannot_cross_analyze_or_read(client, make_key, storage_dir):
    test_key = make_key(client, scopes=ALL_SCOPES, mode="test")
    live_key = make_key(client, scopes=ALL_SCOPES, mode="live")
    test_ds = _upload(client, test_key)
    live_ds = _upload(client, live_key)

    for key, foreign in ((test_key, live_ds), (live_key, test_ds)):
        response = client.post(
            "/v2/analyses",
            headers=_headers(key),
            json={"dataset_id": foreign, "models": ["linear"]},
        )
        assert response.status_code == 404
        assert response.json()["code"] == "not_found"

    mine = client.post(
        "/v2/analyses",
        headers=_headers(test_key),
        json={"dataset_id": test_ds, "models": ["linear"]},
    ).json()
    assert client.get(f"/v2/analyses/{mine['id']}", headers=_headers(live_key)).status_code == 404
    assert client.get("/v2/analyses", headers=_headers(live_key)).json()["data"] == []


def test_analysis_routes_enforce_scopes(client, make_key, storage_dir):
    writer = make_key(client, scopes=["datasets:write", "analyses:read"])
    dataset_id = _upload(client, writer)
    response = client.post(
        "/v2/analyses",
        headers=_headers(writer),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    )
    assert response.status_code == 403
    reader = make_key(client, scopes=["analyses:write"])
    assert client.get("/v2/analyses", headers=_headers(reader)).status_code == 403


def _ten_thousand_rows():
    channels = ["email", "paid_search", "organic", "social", "display"]
    lines = ["timestamp,channel,event_type,customer_id,conversion_value"]
    for customer in range(2000):
        for step in range(5):
            day = 1 + (customer + step) % 27
            hour = (customer * 7 + step * 3) % 24
            converts = step == 4 and customer % 3 == 0
            lines.append(
                f"2026-09-{day:02d}T{hour:02d}:00:00Z,"
                f"{channels[(customer + step) % 5]},"
                f"{'conversion' if converts else 'click'},"
                f"c{customer:05d},{'50.00' if converts else '0'}"
            )
    return ("\n".join(lines) + "\n").encode()


def test_ten_thousand_row_analysis_p95_under_30_seconds(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    content = _ten_thousand_rows()
    dataset_id = _upload(client, key, content=content)
    dataset = client.get(f"/v2/datasets/{dataset_id}", headers=_headers(key)).json()
    assert dataset["status"] == "ready" and dataset["touchpoint_count"] == 10_000

    durations = []
    for model in ("linear", "time_decay", "position_based"):
        started = time.perf_counter()
        created = client.post(
            "/v2/analyses",
            headers=_headers(key),
            json={"dataset_id": dataset_id, "models": [model]},
        ).json()
        analysis = client.get(f"/v2/analyses/{created['id']}", headers=_headers(key)).json()
        durations.append(time.perf_counter() - started)
        assert analysis["status"] == "succeeded"
    # With three samples, the maximum is an upper bound on p95.
    assert max(durations) < 30, durations
