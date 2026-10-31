"""M3c (#18): idempotency, per-key concurrency cap, worker janitor and cancel."""

import asyncio
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.db.models import Analysis

ROOT = Path(__file__).resolve().parents[2]
SAMPLE = ROOT / "examples" / "sample_campaigns.csv"
ALL_SCOPES = ["datasets:write", "datasets:read", "analyses:write", "analyses:read"]


def _headers(key, idempotency_key=None):
    headers = {"Authorization": f"Bearer {key['key']}"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    return headers


def _upload(client, key):
    response = client.post(
        "/v2/datasets",
        headers=_headers(key),
        files={"file": ("campaigns.csv", SAMPLE.read_bytes(), "text/csv")},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def _post(client, key, dataset_id, models=("linear",), idempotency_key=None):
    return client.post(
        "/v2/analyses",
        headers=_headers(key, idempotency_key),
        json={"dataset_id": dataset_id, "models": list(models)},
    )


@pytest.fixture
def storage_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def deferred_worker(client):
    """Stop POST from draining the queue so analyses stay in flight."""
    client.app.state.analysis_inline_worker = False
    yield
    client.app.state.analysis_inline_worker = True


def _update_analysis(client, analysis_id, **fields):
    async def update():
        async with client.app.state.test_session_factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            for name, value in fields.items():
                setattr(analysis, name, value)
            await session.commit()

    asyncio.run(update())


def _count_analyses(client):
    async def count():
        from sqlalchemy import func, select

        async with client.app.state.test_session_factory() as session:
            return (await session.execute(select(func.count(Analysis.id)))).scalar_one()

    return asyncio.run(count())


# --- Idempotency (A2) -------------------------------------------------------


def test_idempotency_replay_returns_the_original_analysis(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)

    first = _post(client, key, dataset_id, idempotency_key="retry-1")
    assert first.status_code == 202, first.text
    assert "Idempotent-Replayed" not in first.headers
    replay = _post(client, key, dataset_id, idempotency_key="retry-1")
    assert replay.status_code == 202, replay.text
    assert replay.json()["id"] == first.json()["id"]
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert _count_analyses(client) == 1

    # Without the header every POST is a new analysis, as before.
    assert _post(client, key, dataset_id).json()["id"] != first.json()["id"]


def test_idempotency_key_with_a_different_body_returns_409(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    assert _post(client, key, dataset_id, ["linear"], "retry-2").status_code == 202

    conflict = _post(client, key, dataset_id, ["first_touch"], "retry-2")
    assert conflict.status_code == 409, conflict.text
    assert conflict.json()["code"] == "idempotency_key_in_use"
    assert _count_analyses(client) == 1


def test_idempotency_keys_are_scoped_per_api_key(client, make_key, storage_dir):
    alice = make_key(client, name="alice", scopes=ALL_SCOPES)
    bob = make_key(client, name="bob", scopes=ALL_SCOPES)
    first = _post(client, alice, _upload(client, alice), idempotency_key="shared")
    second = _post(client, bob, _upload(client, bob), idempotency_key="shared")
    assert first.status_code == second.status_code == 202
    assert first.json()["id"] != second.json()["id"]


def test_idempotency_key_expires_after_24_hours(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    first = _post(client, key, dataset_id, idempotency_key="old").json()
    _update_analysis(
        client, first["id"], created_at=datetime.now(timezone.utc) - timedelta(hours=25)
    )

    # After 24h the key is free again, even with a different body.
    fresh = _post(client, key, dataset_id, ["first_touch"], "old")
    assert fresh.status_code == 202, fresh.text
    assert fresh.json()["id"] != first["id"]
    assert client.get(f"/v2/analyses/{first['id']}", headers=_headers(key)).status_code == 200


def test_idempotency_key_length_is_bounded(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    response = _post(client, key, _upload(client, key), idempotency_key="x" * 256)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_idempotency_key"


# --- Concurrency cap (A4) ---------------------------------------------------


def test_fourth_in_flight_analysis_returns_429(client, make_key, storage_dir, deferred_worker):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    ids = []
    for _ in range(3):
        response = _post(client, key, dataset_id)
        assert response.status_code == 202, response.text
        ids.append(response.json()["id"])

    fourth = _post(client, key, dataset_id)
    assert fourth.status_code == 429, fourth.text
    assert fourth.json()["code"] == "too_many_in_flight_analyses"
    assert int(fourth.headers["Retry-After"]) > 0
    assert _count_analyses(client) == 3

    # Running analyses count too; cancelling one frees a slot.
    _update_analysis(client, ids[0], status="running", started_at=datetime.now(timezone.utc))
    assert _post(client, key, dataset_id).status_code == 429
    cancelled = client.post(f"/v2/analyses/{ids[1]}/cancel", headers=_headers(key))
    assert cancelled.status_code == 200
    assert _post(client, key, dataset_id).status_code == 202


def test_replay_of_in_flight_request_is_not_capped(
    client, make_key, storage_dir, deferred_worker
):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    first = _post(client, key, dataset_id, idempotency_key="a").json()
    _post(client, key, dataset_id)
    _post(client, key, dataset_id)
    replay = _post(client, key, dataset_id, idempotency_key="a")
    assert replay.status_code == 202
    assert replay.json()["id"] == first["id"]


def test_cap_is_per_key_and_configurable(client, make_key, storage_dir, deferred_worker):
    response = client.post(
        "/v2/admin/keys",
        headers={"X-Admin-Bootstrap-Key": "bootstrap-secret"},
        json={"name": "one-at-a-time", "scopes": ALL_SCOPES, "max_concurrent_analyses": 1},
    )
    assert response.status_code == 201, response.text
    narrow = response.json()
    assert narrow["max_concurrent_analyses"] == 1
    other = make_key(client, scopes=ALL_SCOPES)
    assert other.get("max_concurrent_analyses") == 3

    dataset_id = _upload(client, narrow)
    assert _post(client, narrow, dataset_id).status_code == 202
    assert _post(client, narrow, dataset_id).status_code == 429
    # Another key's slots are untouched.
    assert _post(client, other, _upload(client, other)).status_code == 202

    bad = client.post(
        "/v2/admin/keys",
        headers={"X-Admin-Bootstrap-Key": "bootstrap-secret"},
        json={"name": "zero", "scopes": ALL_SCOPES, "max_concurrent_analyses": 0},
    )
    assert bad.status_code == 422


def test_finished_analyses_do_not_count_toward_the_cap(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    # The inline worker finishes each analysis before the next request.
    for _ in range(5):
        assert _post(client, key, dataset_id).status_code == 202


# --- Cancel -----------------------------------------------------------------


def test_cancel_queued_analysis_and_the_worker_skips_it(
    client, make_key, storage_dir, deferred_worker
):
    from src.v2.analyses import process_queued_analyses
    from src.v2.datasets import get_storage

    key = make_key(client, scopes=ALL_SCOPES)
    created = _post(client, key, _upload(client, key)).json()
    response = client.post(f"/v2/analyses/{created['id']}/cancel", headers=_headers(key))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "cancelled"
    assert body["completed_at"] is not None

    factory = client.app.state.test_session_factory
    assert asyncio.run(process_queued_analyses(factory, get_storage())) == 0
    after = client.get(f"/v2/analyses/{created['id']}", headers=_headers(key)).json()
    assert after["status"] == "cancelled"
    assert after["results"] is None


def test_cancel_running_analysis_is_not_overwritten_by_the_worker(
    client, make_key, storage_dir, deferred_worker
):
    from src.v2.analyses import claim_next_analysis, execute_analysis
    from src.v2.datasets import get_storage

    key = make_key(client, scopes=ALL_SCOPES)
    created = _post(client, key, _upload(client, key), ["linear", "first_touch"]).json()
    factory = client.app.state.test_session_factory
    claimed = asyncio.run(claim_next_analysis(factory))
    assert claimed == created["id"]

    response = client.post(f"/v2/analyses/{claimed}/cancel", headers=_headers(key))
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    asyncio.run(execute_analysis(claimed, factory, get_storage()))
    after = client.get(f"/v2/analyses/{claimed}", headers=_headers(key)).json()
    assert after["status"] == "cancelled"
    assert after["results"] is None


def test_cancel_stops_a_running_analysis_between_models(
    client, make_key, storage_dir, deferred_worker, monkeypatch
):
    """A cancel that lands while a model is computing stops the remaining models."""
    from src.v2 import analyses
    from src.v2.datasets import get_storage

    key = make_key(client, scopes=ALL_SCOPES)
    created = _post(client, key, _upload(client, key), ["linear", "first_touch"]).json()
    factory = client.app.state.test_session_factory
    claimed = asyncio.run(analyses.claim_next_analysis(factory))
    real = analyses.compute_model_result
    calls = []

    def compute_then_cancel(frame, model, parameters):
        calls.append(model)
        result = real(frame, model, parameters)
        _update_analysis(client, claimed, status="cancelled",
                         completed_at=datetime.now(timezone.utc))
        return result

    monkeypatch.setattr(analyses, "compute_model_result", compute_then_cancel)
    asyncio.run(analyses.execute_analysis(claimed, factory, get_storage()))
    assert calls == ["linear"]
    after = client.get(f"/v2/analyses/{claimed}", headers=_headers(key)).json()
    assert after["status"] == "cancelled"
    assert after["results"] is None


def test_cancel_finished_unknown_and_scope(client, make_key, storage_dir):
    key = make_key(client, scopes=ALL_SCOPES)
    created = _post(client, key, _upload(client, key)).json()
    done = client.post(f"/v2/analyses/{created['id']}/cancel", headers=_headers(key))
    assert done.status_code == 409
    assert done.json()["code"] == "analysis_not_cancellable"

    missing = client.post("/v2/analyses/nope/cancel", headers=_headers(key))
    assert missing.status_code == 404

    other = make_key(client, name="other", scopes=ALL_SCOPES)
    foreign = client.post(f"/v2/analyses/{created['id']}/cancel", headers=_headers(other))
    assert foreign.status_code == 404

    reader = make_key(client, name="reader", scopes=["analyses:read"])
    denied = client.post(f"/v2/analyses/{created['id']}/cancel", headers=_headers(reader))
    assert denied.status_code == 403


# --- Janitor (T2) -----------------------------------------------------------


def test_janitor_fails_stuck_jobs_and_leaves_healthy_ones(
    client, make_key, storage_dir, deferred_worker
):
    from src.v2.analyses import reap_stuck_analyses

    now = datetime.now(timezone.utc)
    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    # Raise the cap so four analyses can be in flight at once.
    from src.db.models import ApiKey

    async def widen():
        from sqlalchemy import select

        async with client.app.state.test_session_factory() as session:
            row = (await session.execute(select(ApiKey).where(ApiKey.id == key["id"]))).scalar_one()
            row.max_concurrent_analyses = 10
            await session.commit()

    asyncio.run(widen())
    stuck, slow_but_alive, fresh, queued = (
        _post(client, key, dataset_id).json()["id"] for _ in range(4)
    )
    long_ago = now - timedelta(hours=2)
    # Past max runtime and no heartbeat for two hours: a crashed worker.
    _update_analysis(client, stuck, status="running", started_at=long_ago,
                     last_progress_at=long_ago)
    # Past max runtime but still reporting progress: leave it.
    _update_analysis(client, slow_but_alive, status="running", started_at=long_ago,
                     last_progress_at=now - timedelta(seconds=30))
    # Started a minute ago with a stale-looking heartbeat: within max runtime.
    _update_analysis(client, fresh, status="running", started_at=now - timedelta(minutes=1),
                     last_progress_at=now - timedelta(minutes=1))

    factory = client.app.state.test_session_factory
    reaped = asyncio.run(
        reap_stuck_analyses(factory, now=now, max_runtime_minutes=30, stale_after_minutes=5)
    )
    assert reaped == [stuck]

    status = {
        analysis_id: client.get(f"/v2/analyses/{analysis_id}", headers=_headers(key)).json()
        for analysis_id in (stuck, slow_but_alive, fresh, queued)
    }
    assert status[stuck]["status"] == "failed"
    assert status[stuck]["error"]["code"] == "worker_timeout"
    assert status[stuck]["completed_at"] is not None
    assert status[slow_but_alive]["status"] == "running"
    assert status[fresh]["status"] == "running"
    assert status[queued]["status"] == "queued"
    assert status[slow_but_alive]["error"] is None

    # Running again is a no-op.
    assert asyncio.run(
        reap_stuck_analyses(factory, now=now, max_runtime_minutes=30, stale_after_minutes=5)
    ) == []


def test_janitor_failure_is_not_overwritten_by_a_late_worker(
    client, make_key, storage_dir, deferred_worker
):
    from src.v2.analyses import claim_next_analysis, execute_analysis, reap_stuck_analyses
    from src.v2.datasets import get_storage

    key = make_key(client, scopes=ALL_SCOPES)
    created = _post(client, key, _upload(client, key)).json()
    factory = client.app.state.test_session_factory
    claimed = asyncio.run(claim_next_analysis(factory))
    later = datetime.now(timezone.utc) + timedelta(hours=3)
    assert asyncio.run(reap_stuck_analyses(factory, now=later)) == [created["id"]]

    asyncio.run(execute_analysis(claimed, factory, get_storage()))
    after = client.get(f"/v2/analyses/{claimed}", headers=_headers(key)).json()
    assert after["status"] == "failed"
    assert after["error"]["code"] == "worker_timeout"
    assert after["results"] is None


def test_janitor_defaults_come_from_environment(monkeypatch):
    from src.v2.analyses import janitor_settings

    assert janitor_settings() == (30, 5)
    monkeypatch.setenv("RABBIT_ANALYSIS_MAX_RUNTIME_MINUTES", "45")
    monkeypatch.setenv("RABBIT_ANALYSIS_STALE_PROGRESS_MINUTES", "10")
    assert janitor_settings() == (45, 10)


def test_janitor_loop_runs_on_an_interval_and_stops(client, monkeypatch):
    from src.v2 import analyses

    calls = []

    async def fake_reap(session_factory, **kwargs):
        calls.append(session_factory)
        if len(calls) == 2:
            raise RuntimeError("database blip")
        return []

    monkeypatch.setattr(analyses, "reap_stuck_analyses", fake_reap)

    async def drive():
        stop = asyncio.Event()
        task = asyncio.create_task(analyses.run_janitor("factory", interval_seconds=0.01, stop=stop))
        await asyncio.sleep(0.2)
        stop.set()
        await asyncio.wait_for(task, timeout=5)

    asyncio.run(drive())
    # A failed sweep is logged and the loop keeps going.
    assert len(calls) >= 3
    assert set(calls) == {"factory"}


def test_sqlite_migration_adds_max_concurrent_analyses(tmp_path):
    database = tmp_path / "rabbit-v2.sqlite"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database}"
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=ROOT, env=environment, capture_output=True, text=True, check=True,
    )
    with sqlite3.connect(database) as connection:
        columns = {row[1]: row for row in connection.execute("PRAGMA table_info(api_keys)")}
    assert "max_concurrent_analyses" in columns
    assert columns["max_concurrent_analyses"][3] == 1  # NOT NULL
    assert "3" in str(columns["max_concurrent_analyses"][4])  # server default


def test_app_lifespan_starts_and_stops_the_janitor(monkeypatch):
    from fastapi.testclient import TestClient

    import src.main as main
    from src.config import get_settings

    monkeypatch.setattr(get_settings(), "rabbit_v2_enabled", True)
    seen = {}

    async def fake_janitor(session_factory, stop):
        seen["started"] = True
        await stop.wait()
        seen["stopped"] = True

    monkeypatch.setattr(main, "run_janitor", fake_janitor)
    with TestClient(main.create_app()):
        assert seen.get("started") is True
    assert seen.get("stopped") is True

    seen.clear()
    monkeypatch.setenv("RABBIT_ANALYSIS_JANITOR", "0")
    with TestClient(main.create_app()):
        pass
    assert seen == {}


@pytest.mark.parametrize("model", ["first_touch", "last_touch", "linear", "time_decay",
                                   "position_based"])
def test_five_models_on_test_data_stay_pinned(model):
    """docs/b0-baseline.md raw credits (post-#27), normalized to shares."""
    import pandas as pd

    from src.v2.analyses import compute_model_result, resolve_parameters

    raw = {
        "first_touch": {"email": 1.0, "organic": 1.0, "social": 1.0},
        "last_touch": {"email": 2.0, "organic": 1.0},
        "linear": {"email": 1.1666666666666665, "organic": 0.6666666666666666,
                   "paid_search": 0.5833333333333333, "social": 0.5833333333333333},
        "time_decay": {"email": 1.1675575570284877, "organic": 0.6664402106746266,
                       "paid_search": 0.5836586373343504, "social": 0.5823435949625355},
        "position_based": {"email": 1.4000000000000001, "organic": 0.8,
                           "paid_search": 0.29999999999999993, "social": 0.5},
    }[model]
    frame = pd.read_csv(ROOT / "test_data.csv")
    _, result = compute_model_result(frame, model, resolve_parameters(model, None))
    total = sum(raw.values())
    credits = {channel: value["credit"] for channel, value in result["channels"].items()}
    assert credits == pytest.approx({c: v / total for c, v in raw.items()}, abs=1e-12)


def test_concurrent_same_key_request_at_two_of_three_in_flight_replays_not_caps(
    client, make_key, storage_dir, deferred_worker, monkeypatch
):
    """Two same-key POSTs at 2/3 in flight, interleaved: A inserts the third
    analysis after B's pre-lock lookup ran. B's pre-lock lookup is made to miss
    A (the race window); the re-check under the key-row lock must find A and
    replay it instead of returning 429."""
    from src.v2 import analyses

    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    assert _post(client, key, dataset_id).status_code == 202
    assert _post(client, key, dataset_id).status_code == 202  # 2 of 3 in flight
    a = _post(client, key, dataset_id, idempotency_key="race")  # A: now 3 of 3
    assert a.status_code == 202, a.text

    real_find = analyses._find_idempotent
    calls = []

    async def miss_first_lookup(session, key_id, idempotency_key):
        calls.append(idempotency_key)
        if len(calls) == 1:
            return None  # B looked before A's insert was visible
        return await real_find(session, key_id, idempotency_key)

    monkeypatch.setattr(analyses, "_find_idempotent", miss_first_lookup)
    b = _post(client, key, dataset_id, idempotency_key="race")
    assert len(calls) == 2  # pre-lock lookup, then the re-check under the lock
    assert b.status_code == 202, b.text
    assert b.json()["id"] == a.json()["id"]
    assert b.headers["Idempotent-Replayed"] == "true"
    assert _count_analyses(client) == 3


def test_primary_key_conflict_without_idempotency_key_is_reraised(
    client, make_key, storage_dir, deferred_worker, monkeypatch
):
    from sqlalchemy.exc import IntegrityError

    from src.v2 import analyses

    key = make_key(client, scopes=ALL_SCOPES)
    dataset_id = _upload(client, key)
    first = _post(client, key, dataset_id).json()
    monkeypatch.setattr(analyses, "ULID", lambda: first["id"])  # force a PK clash
    looked_up = []

    async def spy(*args):
        looked_up.append(args)
        return None

    monkeypatch.setattr(analyses, "_find_idempotent", spy)
    with pytest.raises(IntegrityError):
        _post(client, key, dataset_id)
    assert looked_up == []


def test_janitor_honours_explicit_zero_thresholds(
    client, make_key, storage_dir, deferred_worker, monkeypatch
):
    from src.v2.analyses import reap_stuck_analyses

    key = make_key(client, scopes=ALL_SCOPES)
    created = _post(client, key, _upload(client, key)).json()
    now = datetime.now(timezone.utc)
    just_now = now - timedelta(seconds=1)
    _update_analysis(client, created["id"], status="running", started_at=just_now,
                     last_progress_at=just_now)
    factory = client.app.state.test_session_factory
    # Defaults (30 / 5 minutes) leave it alone; explicit zeros reap it.
    assert asyncio.run(reap_stuck_analyses(factory, now=now)) == []
    assert asyncio.run(reap_stuck_analyses(
        factory, now=now, max_runtime_minutes=0, stale_after_minutes=0)) == [created["id"]]

    monkeypatch.setenv("RABBIT_ANALYSIS_MAX_RUNTIME_MINUTES", "0")
    monkeypatch.setenv("RABBIT_ANALYSIS_STALE_PROGRESS_MINUTES", "0")
    from src.v2.analyses import janitor_settings

    assert janitor_settings() == (0, 0)
