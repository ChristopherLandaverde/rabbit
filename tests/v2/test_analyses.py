"""Async analyses: submit, poll, and read results (#16) and comparisons (#17)."""

import asyncio
import json
import math
import time
from pathlib import Path

import pytest

from src.db.models import Dataset

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "examples" / "sample_campaigns.csv"
# The sample dataset is symmetric: every model gives each channel 20%. The
# regression file test_data.csv separates the models, so both are checked.
REFERENCE = ROOT / "test_data.csv"
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


@pytest.mark.parametrize("data_file", [SAMPLE, REFERENCE], ids=["sample", "test_data"])
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
def test_end_to_end_credits_match_v1(
    client, make_key, storage_dir, model, options, v1_params, data_file
):
    """API key -> upload dataset -> validate -> analyze -> result equals v1 output."""
    key = make_key(client, scopes=ALL_SCOPES, mode="test")
    dataset_id = _upload(client, key, content=data_file.read_bytes())
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
    expected = _v1_credits(client, data_file.read_bytes(), model, **v1_params)
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


def test_linear_on_reference_file_matches_recorded_baseline(client, make_key, storage_dir):
    """Anchor to docs/b0-baseline.md raw linear credits, normalized to shares."""
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=REFERENCE.read_bytes())
    created = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear"]},
    ).json()
    channels = client.get(f"/v2/analyses/{created['id']}", headers=_headers(key)).json()[
        "results"
    ]["linear"]["channels"]
    raw = {"email": 1.1666666666666665, "organic": 0.6666666666666666,
           "paid_search": 0.5833333333333333, "social": 0.5833333333333333}
    total = sum(raw.values())
    assert {c: v["credit"] for c, v in channels.items()} == pytest.approx(
        {c: v / total for c, v in raw.items()}
    )


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
        ({"models": ["linear", "first_touch", "last_touch", "time_decay", "position_based", "linear"]}, "too_many_models"),
        ({"models": ["linear", "linear"]}, "validation_failed"),
        ({"models": ["linear"], "options": {"time_decay_half_life_days": 0}}, "validation_failed"),
        ({"models": ["position_based"], "options": {"position_based_weights": {"first": 0.7, "last": 0.6}}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": 0}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": -30}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": 1.5}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": True}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": "30"}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": 3651}}, "validation_failed"),
        ({"models": ["linear"], "options": {"conversion_window_days": 1e308}}, "validation_failed"),
        ({"models": ["linear"], "options": {"lookback": 30}}, "validation_failed"),
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


# --- Multi-model analyses and the comparison block (#17) ---------------------

FIVE_MODELS = ["linear", "time_decay", "first_touch", "last_touch", "position_based"]
GOLDEN = json.loads((Path(__file__).parent / "golden" / "jsd_golden.json").read_text())

# Two customers, each touched by social and then converting on email.
# first_touch = {social: 1}, last_touch = {email: 1}, linear = {social: .5, email: .5}.
SOCIAL_THEN_EMAIL = (
    b"timestamp,channel,event_type,customer_id,conversion_value\n"
    b"2026-09-01T10:00:00Z,social,click,c1,0\n"
    b"2026-09-01T12:00:00Z,email,conversion,c1,40.00\n"
    b"2026-09-02T10:00:00Z,social,click,c2,0\n"
    b"2026-09-02T12:00:00Z,email,conversion,c2,60.00\n"
)


def _run(client, key, dataset_id, models, options=None, query=""):
    body = {"dataset_id": dataset_id, "models": models}
    if options is not None:
        body["options"] = options
    submitted = client.post("/v2/analyses", headers=_headers(key), json=body)
    assert submitted.status_code == 202, submitted.text
    created = submitted.json()
    analysis = client.get(f"/v2/analyses/{created['id']}{query}", headers=_headers(key))
    assert analysis.status_code == 200, analysis.text
    return created, analysis.json()


def test_five_model_analysis_returns_results_and_comparison(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    content = REFERENCE.read_bytes()
    dataset_id = _upload(client, key, content=content)
    created, analysis = _run(client, key, dataset_id, FIVE_MODELS)

    assert created["models"] == FIVE_MODELS
    assert analysis["status"] == "succeeded", analysis
    assert analysis["progress"] == {"models_completed": 5, "models_total": 5}
    assert set(analysis["results"]) == set(FIVE_MODELS)  # JSONB does not keep key order

    # Every model's credits are unchanged from v1 /attribution/analyze.
    for model in FIVE_MODELS:
        expected = _v1_credits(client, content, model)["channel_attributions"]
        got = analysis["results"][model]["channels"]
        assert {c: v["credit"] for c, v in got.items()} == {
            c: v["credit"] for c, v in expected.items()
        }

    comparison = analysis["comparison"]
    assert comparison["model_agreement_method"] == "jensen_shannon"
    result_channels = set().union(*(analysis["results"][m]["channels"] for m in FIVE_MODELS))
    assert set(comparison["channels"]) == result_channels
    for channel, entry in comparison["channels"].items():
        # Thin (C4): channel keys and per-model credit only; no revenue or conversions.
        assert set(entry) == {
            "credit_by_model", "credit_spread", "most_favorable_model", "least_favorable_model",
        }
        assert set(entry["credit_by_model"]) == set(FIVE_MODELS)
        for model, credit in entry["credit_by_model"].items():
            channels = analysis["results"][model]["channels"]
            assert credit == (channels[channel]["credit"] if channel in channels else 0.0)
        values = entry["credit_by_model"].values()
        assert entry["credit_spread"] == pytest.approx(max(values) - min(values))
        assert entry["credit_by_model"][entry["most_favorable_model"]] == max(values)
        assert entry["credit_by_model"][entry["least_favorable_model"]] == min(values)

    # paid_search gets nothing under either single-touch model (README table).
    paid = comparison["channels"]["paid_search"]
    assert paid["credit_by_model"]["first_touch"] == 0.0
    assert paid["credit_by_model"]["last_touch"] == 0.0
    assert paid["least_favorable_model"] == "first_touch"

    recorded = GOLDEN["recorded_cases"]["test_data_csv_five_models"]
    assert recorded["models"] == FIVE_MODELS
    assert comparison["model_agreement_score"] == pytest.approx(
        recorded["model_agreement_score"], abs=1e-12
    )
    assert "impact" not in str(comparison).lower()


def test_agreement_score_end_to_end_matches_hand_computed_value(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=SOCIAL_THEN_EMAIL)

    # first_touch {social: 1} vs last_touch {email: 1}: disjoint, JSD = 1, agreement 0.
    _, disjoint = _run(client, key, dataset_id, ["first_touch", "last_touch"])
    assert disjoint["comparison"]["model_agreement_score"] == pytest.approx(0.0, abs=1e-12)

    # Add linear {social: .5, email: .5}. Pairs: (ft, lt) = 1; (ft, linear) and
    # (lt, linear) are each the golden partial_overlap_subset case,
    # 1.5 - 0.75 * log2(3). Mean = (4 - 1.5 * log2 3) / 3, so
    # agreement = 0.5 * log2(3) - 1/3 = 0.4591479170272448.
    _, three = _run(client, key, dataset_id, ["first_touch", "last_touch", "linear"])
    assert three["comparison"]["model_agreement_score"] == pytest.approx(
        0.5 * math.log2(3) - 1 / 3, abs=1e-12
    )
    email = three["comparison"]["channels"]["email"]
    assert email["credit_by_model"] == {"first_touch": 0.0, "last_touch": 1.0, "linear": 0.5}
    assert email["credit_spread"] == 1.0
    assert email["most_favorable_model"] == "last_touch"
    assert email["least_favorable_model"] == "first_touch"

    # Identical distributions agree perfectly (2-touch position_based splits evenly).
    _, same = _run(client, key, dataset_id, ["linear", "position_based"])
    assert same["comparison"]["model_agreement_score"] == pytest.approx(1.0, abs=1e-12)


def test_single_model_analysis_has_no_comparison(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=REFERENCE.read_bytes())
    _, analysis = _run(client, key, dataset_id, ["linear"])
    assert analysis["status"] == "succeeded"
    assert analysis["comparison"] is None


def test_progress_counts_each_completed_model(
    client, make_key, storage_dir, deferred_worker, monkeypatch
):
    from src.db.models import Analysis
    from src.v2 import analyses
    from src.v2.datasets import get_storage

    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=REFERENCE.read_bytes())
    created = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": FIVE_MODELS},
    ).json()
    factory = client.app.state.test_session_factory
    real = analyses.compute_model_result
    seen = []

    async def read_progress():
        async with factory() as session:
            return (await session.get(Analysis, created["id"])).progress

    async def drive():
        loop = asyncio.get_running_loop()

        def spy(frame, model, parameters):
            # Runs in the worker thread: read committed progress before this model.
            progress = asyncio.run_coroutine_threadsafe(read_progress(), loop).result(5)
            seen.append((model, progress["models_completed"], progress["models_total"]))
            return real(frame, model, parameters)

        monkeypatch.setattr(analyses, "compute_model_result", spy)
        await analyses.process_queued_analyses(factory, get_storage())

    asyncio.run(drive())
    assert seen == [(model, index, 5) for index, model in enumerate(FIVE_MODELS)]
    done = client.get(f"/v2/analyses/{created['id']}", headers=_headers(key)).json()
    assert done["progress"] == {"models_completed": 5, "models_total": 5}


def test_options_apply_to_their_models_in_a_multi_model_analysis(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    content = REFERENCE.read_bytes()
    dataset_id = _upload(client, key, content=content)
    options = {
        "time_decay_half_life_days": 0.5,
        "position_based_weights": {"first": 0.3, "last": 0.5},
    }
    created, analysis = _run(client, key, dataset_id, FIVE_MODELS, options)
    assert created["options"] == options
    results = analysis["results"]
    assert results["time_decay"]["parameters"] == {"half_life_days": 0.5}
    assert results["position_based"]["parameters"]["first_touch_weight"] == 0.3
    assert results["linear"]["parameters"] == {}
    for model, params in (
        ("time_decay", {"half_life_days": 0.5}),
        ("position_based", {"first_touch_weight": 0.3, "last_touch_weight": 0.5}),
    ):
        expected = _v1_credits(client, content, model, **params)["channel_attributions"]
        assert {c: v["credit"] for c, v in results[model]["channels"].items()} == {
            c: v["credit"] for c, v in expected.items()
        }


def test_conversion_window_excludes_touchpoints_older_than_the_window(
    client, make_key, storage_dir
):
    # social 40 days before the conversion, paid_search 1 day before, conversion on email.
    content = (
        b"timestamp,channel,event_type,customer_id,conversion_value\n"
        b"2026-08-01T10:00:00Z,social,click,c1,0\n"
        b"2026-09-09T10:00:00Z,paid_search,click,c1,0\n"
        b"2026-09-10T10:00:00Z,email,conversion,c1,80.00\n"
    )
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=content)

    _, unwindowed = _run(client, key, dataset_id, ["first_touch", "linear"])
    assert set(unwindowed["results"]["first_touch"]["channels"]) == {"social"}

    _, windowed = _run(
        client, key, dataset_id, ["first_touch", "linear"], {"conversion_window_days": 30}
    )
    results = windowed["results"]
    assert set(results["first_touch"]["channels"]) == {"paid_search"}
    assert {c: v["credit"] for c, v in results["linear"]["channels"].items()} == pytest.approx(
        {"paid_search": 0.5, "email": 0.5}
    )
    assert results["linear"]["parameters"] == {"conversion_window_days": 30}
    assert windowed["summary"]["total_conversions"] == 1
    assert windowed["summary"]["total_revenue"] == 80.0
    assert "social" not in windowed["comparison"]["channels"]

    # A window wide enough to cover every touchpoint changes nothing.
    _, wide = _run(
        client, key, dataset_id, ["first_touch", "linear"], {"conversion_window_days": 90}
    )
    assert wide["results"]["linear"]["channels"] == unwindowed["results"]["linear"]["channels"]


def test_journey_block_is_opt_in(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=REFERENCE.read_bytes())
    created, plain = _run(client, key, dataset_id, ["linear", "last_touch"])
    assert "journey" not in plain

    url = f"/v2/analyses/{created['id']}"
    with_journey = client.get(f"{url}?include=journey", headers=_headers(key))
    assert with_journey.status_code == 200
    body = with_journey.json()
    assert body["comparison"] == plain["comparison"]
    journey = body["journey"]
    assert set(journey) == {"journey_lengths", "conversion_paths", "time_to_conversion"}
    assert journey["journey_lengths"]["average_length"] == pytest.approx(10 / 3)
    assert journey["journey_lengths"]["length_distribution"]["3_5_touchpoints"] == 3
    paths = {p["path"]: p["frequency"] for p in journey["conversion_paths"]["top_paths"]}
    assert paths == {
        "email -> paid_search -> social -> email": 1,
        "organic -> paid_search -> email": 1,
        "social -> email -> organic": 1,
    }
    assert journey["time_to_conversion"]["time_distribution"]["same_day"] == 3
    # The descriptive block carries none of the analyzer's rule-generated advice.
    assert "insights" not in str(journey)

    bad = client.get(f"{url}?include=bogus", headers=_headers(key))
    assert bad.status_code == 422
    assert bad.json()["code"] == "validation_failed"


def test_journey_and_comparison_are_null_until_the_analysis_succeeds(
    client, make_key, storage_dir, deferred_worker
):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    created = client.post(
        "/v2/analyses",
        headers=_headers(key),
        json={"dataset_id": dataset_id, "models": ["linear", "last_touch"]},
    ).json()
    assert created["progress"] is None
    queued = client.get(
        f"/v2/analyses/{created['id']}?include=journey", headers=_headers(key)
    ).json()
    assert queued["status"] == "queued"
    assert queued["journey"] is None
    assert queued["comparison"] is None


def test_ten_thousand_row_five_model_analysis_under_30_seconds(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key, content=_ten_thousand_rows())
    started = time.perf_counter()
    _, analysis = _run(client, key, dataset_id, FIVE_MODELS)
    elapsed = time.perf_counter() - started
    assert analysis["status"] == "succeeded"
    assert analysis["comparison"]["model_agreement_score"] is not None
    assert elapsed < 30, elapsed
