"""rabbit-mcp: the local stdio MCP server over the engine and the v2 API (L2).

Every tool is called through a real MCP client session (in-process memory
streams, plus one stdio subprocess). BigQuery is the mocked client from
tests/fixtures/ga4_bigquery.py; no Google API is called.
"""

import asyncio
import json
import os
import re
import sys
from contextlib import nullcontext
from pathlib import Path

import pandas as pd
import pytest

pytest.importorskip("mcp")

from mcp import StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402
from mcp.client.session import ClientSession  # noqa: E402
from mcp.shared.memory import create_connected_server_and_client_session  # noqa: E402

from src.importers import ga4_bigquery as ga4  # noqa: E402
from src.mcp_server import server as rabbit_mcp  # noqa: E402
from src.v2.analyses import compute_model_result, resolve_parameters  # noqa: E402
from src.v2.comparison import build_comparison  # noqa: E402
from tests.fixtures.ga4_bigquery import EQUIVALENT_CSV, FakeBigQueryClient  # noqa: E402
from tests.v2.test_ga4_bigquery_importer import TEST_DATA_GOLDEN  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
TEST_DATA = ROOT / "test_data.csv"
FIVE_MODELS = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]
TOOLS = {"import_ga4", "run_models", "compare_models", "dataset_quality"}
GA4_ARGS = {"project": "demo-project-123", "dataset": "analytics_123456789",
            "start": "20250301", "end": "20250315", "conversion_event": "purchase"}


def _session_call(*calls):
    """Open one in-process MCP session and run ``calls`` (name, args) in order."""

    async def go():
        async with create_connected_server_and_client_session(
            rabbit_mcp.build_server()
        ) as session:
            out = []
            for name, args in calls:
                out.append(await session.call_tool(name, args))
            return out

    return asyncio.run(go())


def call(name, args):
    return _session_call((name, args))[0]


def ok(result):
    assert result.isError is False, result.content[0].text
    body = result.structuredContent
    assert json.loads(result.content[0].text) == body
    assert_meaning(body)
    return body


def error(result):
    assert result.isError is True
    body = result.structuredContent
    assert json.loads(result.content[0].text) == body
    assert_meaning(body)
    return body["error"]


def assert_meaning(body):
    meaning = body["meaning"].lower()
    assert "association under the named" in meaning and "not causal" in meaning


def credits(model_result):
    return {channel: values["credit"] for channel, values in model_result["channels"].items()}


@pytest.fixture
def fake_bigquery(monkeypatch):
    clients = []

    def factory(**kwargs):
        client = FakeBigQueryClient(**kwargs) if kwargs else FakeBigQueryClient()
        clients.append(client)
        return client

    monkeypatch.setattr(rabbit_mcp, "BIGQUERY_CLIENT_FACTORY", factory)
    return clients


# --- tool surface ----------------------------------------------------------------


def test_lists_the_four_read_tools_with_the_meaning_sentence():
    async def go():
        async with create_connected_server_and_client_session(
            rabbit_mcp.build_server()
        ) as session:
            return (await session.list_tools()).tools

    tools = asyncio.run(go())
    assert {tool.name for tool in tools} == TOOLS
    for tool in tools:
        description = tool.description.lower()
        assert "association under the named" in description, tool.name
        assert "not causal" in description, tool.name
        assert tool.annotations.destructiveHint is False
    by_name = {tool.name: tool for tool in tools}
    for name in ("run_models", "compare_models", "dataset_quality"):
        assert by_name[name].annotations.readOnlyHint is True


def test_no_tool_accepts_credentials():
    async def go():
        async with create_connected_server_and_client_session(
            rabbit_mcp.build_server()
        ) as session:
            return (await session.list_tools()).tools

    secret = re.compile(r"cred|secret|token|passw|auth|api_?key|key_?file|bearer|adc", re.I)
    for tool in asyncio.run(go()):
        names = set(tool.inputSchema.get("properties", {}))
        assert not {name for name in names if secret.search(name)}, (tool.name, names)
    import_args = {
        tool.name: set(tool.inputSchema["properties"]) for tool in asyncio.run(go())
    }["import_ga4"]
    assert import_args == {"project", "dataset", "start", "end", "conversion_event",
                           "max_bytes", "out_path"}


# --- run_models / compare_models / dataset_quality on a local file ---------------


def test_run_models_on_test_data_equals_pinned_outputs():
    body = ok(call("run_models", {"touchpoints_path": str(TEST_DATA)}))
    assert body["source"] == {"type": "file", "path": str(TEST_DATA)}
    assert body["models"] == FIVE_MODELS
    for model in FIVE_MODELS:
        result = body["results"][model]
        assert result["model"] == model
        assert credits(result) == pytest.approx(TEST_DATA_GOLDEN[model], abs=1e-12)
    assert body["summary"]["total_conversions"] == 3
    assert body["summary"]["total_revenue"] == 225.0
    assert body["interpretation"]["type"] == "association"


def test_run_models_subset_and_options_match_the_engine():
    body = ok(call("run_models", {
        "touchpoints_path": str(TEST_DATA),
        "models": ["time_decay", "position_based"],
        "options": {"time_decay_half_life_days": 0.5,
                    "position_based_weights": {"first": 0.3, "last": 0.5}},
    }))
    frame = pd.read_csv(TEST_DATA, dtype={"customer_id": str})
    for model in ("time_decay", "position_based"):
        parameters = resolve_parameters(model, {
            "time_decay_half_life_days": 0.5,
            "position_based_weights": {"first": 0.3, "last": 0.5},
        })
        _, expected = compute_model_result(frame, model, parameters)
        assert body["results"][model]["parameters"] == pytest.approx(expected["parameters"])
        assert credits(body["results"][model]) == pytest.approx(credits(expected), abs=1e-12)


def test_compare_models_returns_the_engine_jsd_block():
    body = ok(call("compare_models", {"touchpoints_path": str(TEST_DATA)}))
    expected = build_comparison(
        FIVE_MODELS,
        {model: {"channels": {c: {"credit": v} for c, v in TEST_DATA_GOLDEN[model].items()}}
         for model in FIVE_MODELS},
    )
    assert body["comparison"]["model_agreement_method"] == "jensen_shannon"
    assert body["comparison"]["model_agreement_score"] == pytest.approx(
        expected["model_agreement_score"], abs=1e-12)
    assert set(body["comparison"]["channels"]) == set(expected["channels"])
    assert "agreement between models is not evidence" in body["interpretation"]["statement"]


def test_compare_models_needs_two_models():
    err = error(call("compare_models", {"touchpoints_path": str(TEST_DATA),
                                        "models": ["linear"]}))
    assert err["code"] == "validation_failed"


def test_dataset_quality_reports_the_existing_validation(tmp_path):
    body = ok(call("dataset_quality", {"touchpoints_path": str(TEST_DATA)}))
    assert body["status"] == "ready"
    assert body["validation"] == {"errors": [], "warnings": []}
    assert body["touchpoint_count"] == len(pd.read_csv(TEST_DATA))
    assert body["unique_customers"] == 3

    bad = tmp_path / "bad.csv"
    bad.write_text("when,where\n2024-01-01,email\n")
    body = ok(call("dataset_quality", {"touchpoints_path": str(bad)}))
    assert body["status"] == "invalid"
    errors = body["validation"]["errors"]
    assert {issue["code"] for issue in errors} == {"missing_required_column"}
    assert {issue["column"] for issue in errors} == {"timestamp", "channel", "event_type"}

    garbled = tmp_path / "garbled.parquet"
    garbled.write_bytes(b"not parquet")
    body = ok(call("dataset_quality", {"touchpoints_path": str(garbled)}))
    assert body["status"] == "invalid"
    assert body["validation"]["errors"][0]["code"] == "invalid_file_format"


# --- bad input gives a structured error --------------------------------------------


@pytest.mark.parametrize("args,code", [
    ({}, "invalid_source"),
    ({"touchpoints_path": "x.csv", "dataset_id": "ds_1"}, "invalid_source"),
    ({"touchpoints_path": "/nonexistent/rabbit/touchpoints.csv"}, "file_not_found"),
    ({"touchpoints_path": str(TEST_DATA), "models": ["shapley"]}, "unknown_model"),
    ({"touchpoints_path": str(TEST_DATA), "models": ["linear", "linear"]}, "validation_failed"),
    ({"touchpoints_path": str(TEST_DATA), "options": {"time_decay_half_life_days": -1}},
     "validation_failed"),
    ({"touchpoints_path": str(ROOT / "README.md")}, "unsupported_file_type"),
])
def test_run_models_bad_input_is_a_structured_error(args, code):
    err = error(call("run_models", args))
    assert err["code"] == code
    assert err["message"]


def test_run_models_on_an_invalid_file_returns_the_validation_errors(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("when,where\n2024-01-01,email\n")
    err = error(call("run_models", {"touchpoints_path": str(bad)}))
    assert err["code"] == "dataset_invalid"
    assert err["validation"]["errors"]


def test_dataset_id_without_api_configuration_is_a_structured_error(monkeypatch):
    monkeypatch.delenv("RABBIT_URL", raising=False)
    monkeypatch.delenv("RABBIT_API_KEY", raising=False)
    for tool in ("run_models", "compare_models", "dataset_quality"):
        err = error(call(tool, {"dataset_id": "01HXYZ"}))
        assert err["code"] == "api_not_configured"
        assert "RABBIT_API_KEY" in err["message"]


# --- import_ga4 against the mocked BigQuery client ----------------------------------


def test_import_ga4_returns_summary_and_writes_a_temp_csv(fake_bigquery):
    body = ok(call("import_ga4", GA4_ARGS))
    direct = ga4.import_ga4(client=FakeBigQueryClient(), **GA4_ARGS)
    assert body["touchpoints"] == len(direct.frame) == 16
    assert body["conversions"] == 4 and body["session_starts"] == 12
    assert body["customers"] == direct.frame["customer_id"].nunique()
    assert body["stats"] == direct.stats
    assert body["estimated_bytes"] == 52_428_800
    assert body["source_rows"] == 16
    path = Path(body["csv_path"])
    try:
        assert path.is_absolute() and path.exists()
        written = pd.read_csv(path, dtype=str, keep_default_na=False)
        assert list(written.columns) == ga4.TOUCHPOINT_COLUMNS
        assert len(written) == 16
        # The same dry run then capped query as the CLI.
        dry, real = fake_bigquery[0].queries
        assert dry["job_config"].dry_run is True
        assert real["job_config"].maximum_bytes_billed == ga4.DEFAULT_MAX_BYTES

        # The imported file runs through the same engine as the equivalent CSV.
        from_import = ok(call("run_models", {"touchpoints_path": str(path)}))
        from_csv = ok(call("run_models", {"touchpoints_path": str(EQUIVALENT_CSV)}))
        for model in FIVE_MODELS:
            assert credits(from_import["results"][model]) == pytest.approx(
                credits(from_csv["results"][model]), abs=1e-12)
    finally:
        path.unlink(missing_ok=True)


def test_import_ga4_writes_only_to_the_path_given(fake_bigquery, tmp_path):
    out = tmp_path / "ga4.csv"
    body = ok(call("import_ga4", {**GA4_ARGS, "out_path": str(out), "max_bytes": 100_000_000}))
    assert body["csv_path"] == str(out.resolve())
    assert out.exists()
    assert fake_bigquery[0].queries[1]["job_config"].maximum_bytes_billed == 100_000_000

    again = error(call("import_ga4", {**GA4_ARGS, "out_path": str(out)}))
    assert again["code"] == "output_exists"
    missing_dir = error(call("import_ga4", {**GA4_ARGS, "out_path": str(tmp_path / "no" / "x.csv")}))
    assert missing_dir["code"] == "invalid_argument"
    relative = error(call("import_ga4", {**GA4_ARGS, "out_path": "relative.csv"}))
    assert relative["code"] == "invalid_argument"


def test_import_ga4_byte_guard_refuses_before_querying(monkeypatch):
    clients = []

    def factory():
        clients.append(FakeBigQueryClient(estimated_bytes=2_000_000))
        return clients[-1]

    monkeypatch.setattr(rabbit_mcp, "BIGQUERY_CLIENT_FACTORY", factory)
    err = error(call("import_ga4", {**GA4_ARGS, "max_bytes": 1_000_000}))
    assert err["code"] == "byte_limit_exceeded"
    assert err["exit_code"] == ga4.EXIT_REFUSED == 3
    assert err["estimated_bytes"] == 2_000_000 and err["max_bytes"] == 1_000_000
    assert "Nothing was queried" in err["message"]
    assert len(clients[0].queries) == 1 and clients[0].queries[0]["job_config"].dry_run is True


@pytest.mark.parametrize("make_error,code,exit_code", [
    (lambda e: e.Forbidden("made-up failure"), "access_denied", 5),
    (lambda e: e.NotFound("made-up failure"), "no_export_tables", 2),
    (lambda e: e.InternalServerError("made-up failure"), "bigquery_error", 6),
    (lambda e: e.BadRequest("Query exceeded limit for bytes billed",
                            errors=[{"reason": "bytesBilledLimitExceeded"}]),
     "bytes_billed_exceeded", 4),
])
def test_import_ga4_errors_keep_the_cli_exit_semantics(monkeypatch, make_error, code, exit_code):
    from google.api_core import exceptions

    monkeypatch.setattr(rabbit_mcp, "BIGQUERY_CLIENT_FACTORY",
                        lambda: FakeBigQueryClient(query_error=make_error(exceptions)))
    err = error(call("import_ga4", GA4_ARGS))
    assert (err["code"], err["exit_code"]) == (code, exit_code)


def test_import_ga4_invalid_arguments_and_missing_adc(monkeypatch, fake_bigquery):
    err = error(call("import_ga4", {**GA4_ARGS, "start": "2025-03-01"}))
    assert (err["code"], err["exit_code"]) == ("invalid_argument", 2)
    err = error(call("import_ga4", {**GA4_ARGS, "max_bytes": 0}))
    assert err["code"] == "invalid_argument"
    assert fake_bigquery == [] or all(not c.queries for c in fake_bigquery)

    # Without a test factory the importer asks ADC for credentials itself.
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError

    monkeypatch.setattr(rabbit_mcp, "BIGQUERY_CLIENT_FACTORY", None)

    def no_adc(scopes=None):
        raise DefaultCredentialsError("none")

    monkeypatch.setattr(google.auth, "default", no_adc)
    err = error(call("import_ga4", GA4_ARGS))
    assert (err["code"], err["exit_code"]) == ("access_denied", 5)
    assert "gcloud auth application-default login" in err["message"]


# --- dataset_id through the v2 API --------------------------------------------------


@pytest.fixture
def v2_api(client, make_key, monkeypatch, tmp_path):
    """Point the MCP server at the in-process v2 app with a key from env."""
    monkeypatch.setenv("RABBIT_STORAGE_DIR", str(tmp_path))
    key = make_key(client, scopes=["datasets:write", "datasets:read",
                                   "analyses:write", "analyses:read"])
    monkeypatch.setenv("RABBIT_URL", "http://localhost")
    monkeypatch.setenv("RABBIT_API_KEY", key["key"])
    monkeypatch.setattr(rabbit_mcp, "API_CLIENT_FACTORY", lambda base_url: nullcontext(client))
    response = client.post(
        "/v2/datasets", headers={"Authorization": f"Bearer {key['key']}"},
        files={"file": ("test_data.csv", TEST_DATA.read_bytes(), "text/csv")},
    )
    assert response.status_code == 202, response.text
    return response.json()["id"]


def test_dataset_id_tools_use_the_v2_api(v2_api):
    run, compare, quality = (ok(r) for r in _session_call(
        ("run_models", {"dataset_id": v2_api}),
        ("compare_models", {"dataset_id": v2_api, "models": ["first_touch", "last_touch"]}),
        ("dataset_quality", {"dataset_id": v2_api}),
    ))
    assert run["source"]["type"] == "v2_api" and run["source"]["dataset_id"] == v2_api
    assert run["source"]["analysis_id"]
    for model in FIVE_MODELS:
        assert credits(run["results"][model]) == pytest.approx(TEST_DATA_GOLDEN[model], abs=1e-12)
    local = ok(call("compare_models", {"touchpoints_path": str(TEST_DATA),
                                       "models": ["first_touch", "last_touch"]}))
    assert compare["comparison"]["model_agreement_score"] == pytest.approx(
        local["comparison"]["model_agreement_score"], abs=1e-12)
    assert quality["status"] == "ready"
    assert quality["touchpoint_count"] == len(pd.read_csv(TEST_DATA))
    assert quality["source"] == {"type": "v2_api", "dataset_id": v2_api}


def test_v2_api_problems_become_structured_errors(v2_api):
    err = error(call("run_models", {"dataset_id": "01NOTADATASET0000000000000"}))
    assert (err["code"], err["status"]) == ("not_found", 404)
    err = error(call("dataset_quality", {"dataset_id": "01NOTADATASET0000000000000"}))
    assert err["code"] == "not_found"


# --- the real stdio transport -------------------------------------------------------


def test_stdio_server_runs_as_a_module_and_keeps_stdout_clean(tmp_path):
    """`python -m src.mcp_server` from another directory, as an agent launches it."""
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "src.mcp_server"],
        env={**os.environ, "PYTHONPATH": str(ROOT)},
        cwd=str(tmp_path),
    )

    async def go():
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                tools = await session.list_tools()
                result = await session.call_tool(
                    "run_models", {"touchpoints_path": str(TEST_DATA), "models": ["linear"]}
                )
                return init, tools, result

    init, tools, result = asyncio.run(go())
    assert init.serverInfo.name == "rabbit-mcp"
    assert {tool.name for tool in tools.tools} == TOOLS
    body = ok(result)
    assert credits(body["results"]["linear"]) == pytest.approx(TEST_DATA_GOLDEN["linear"])


def _noisy_touchpoints(tmp_path):
    """test_data.csv with negative conversion values: the journey builder
    prints an "Error creating touchpoint" block to stdout for each one."""
    frame = pd.read_csv(TEST_DATA, dtype=str, keep_default_na=False)
    frame.loc[frame["event_type"] == "conversion", "conversion_value"] = "-5"
    path = tmp_path / "noisy.csv"
    frame.to_csv(path, index=False)
    return path


def test_concurrent_calls_over_real_stdio_keep_stdout_pure_json_rpc(tmp_path):
    """Engine prints during concurrent tool calls must not reach the protocol
    stream: every stdout line parses as JSON-RPC and every call gets a reply."""
    noisy = str(_noisy_touchpoints(tmp_path))
    calls = []
    for index in range(12):
        name = ("run_models", "compare_models", "dataset_quality")[index % 3]
        args = {"touchpoints_path": noisy}
        calls.append({"jsonrpc": "2.0", "id": 100 + index, "method": "tools/call",
                      "params": {"name": name, "arguments": args}})

    async def go():
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-m", "src.mcp_server",
            cwd=str(tmp_path), env={**os.environ, "PYTHONPATH": str(ROOT)},
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        def send(message):
            process.stdin.write((json.dumps(message) + "\n").encode())

        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-06-18", "capabilities": {},
            "clientInfo": {"name": "stdio-purity-test", "version": "0"}}})
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        for call in calls:  # all at once: the server handles them concurrently
            send(call)
        await process.stdin.drain()

        lines, replies = [], {}
        wanted = {1} | {call["id"] for call in calls}
        try:
            while not wanted <= set(replies):
                raw = await asyncio.wait_for(process.stdout.readline(), timeout=60)
                if not raw:
                    break
                lines.append(raw.decode())
                try:
                    message = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(message, dict) and "id" in message:
                    replies[message["id"]] = message
        finally:
            process.stdin.close()
            try:
                await asyncio.wait_for(process.wait(), timeout=10)
            except TimeoutError:
                process.kill()
                await process.wait()
            stderr = (await process.stderr.read()).decode()
        return lines, replies, stderr

    lines, replies, stderr = asyncio.run(go())
    for line in lines:
        message = json.loads(line)  # fails on any non-JSON line
        assert message.get("jsonrpc") == "2.0", line
    assert set(replies) == {1} | {call["id"] for call in calls}
    for call in calls:
        assert "result" in replies[call["id"]], replies[call["id"]]
    # The prints happened; they went to stderr.
    assert "Error creating touchpoint" in stderr


# --- v2 API client hardening ---------------------------------------------------------


def _mock_api(monkeypatch, handler):
    """Serve the MCP server's API calls from ``handler`` (an httpx MockTransport)."""
    import httpx

    seen = []

    def record(request):
        seen.append(request)
        return handler(request)

    monkeypatch.setenv("RABBIT_URL", "https://rabbit.example")
    monkeypatch.setenv("RABBIT_API_KEY", "rk_test_fromenv")
    monkeypatch.setattr(
        rabbit_mcp, "API_CLIENT_FACTORY",
        lambda base_url: httpx.Client(base_url=base_url, transport=httpx.MockTransport(record)),
    )
    sleeps = []
    monkeypatch.setattr(rabbit_mcp.time, "sleep", sleeps.append)
    return seen, sleeps


SUCCEEDED = {"id": "an_1", "status": "succeeded", "models": ["linear"], "summary": {},
             "results": {"linear": {"model": "linear", "parameters": {}, "channels": {}}},
             "comparison": None,
             "interpretation": {"type": "association", "statement": "x"}}


def test_analysis_post_sends_an_idempotency_key_and_retries_429(monkeypatch):
    import httpx

    posts = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/v2/analyses":
            posts.append(request)
            if len(posts) == 1:
                return httpx.Response(429, headers={"Retry-After": "7"}, json={
                    "code": "too_many_in_flight_analyses", "detail": "busy"})
            return httpx.Response(202, json={"id": "an_1", "status": "queued"})
        return httpx.Response(200, json=SUCCEEDED)

    seen, sleeps = _mock_api(monkeypatch, handler)
    ok(call("run_models", {"dataset_id": "ds_1", "models": ["linear"]}))
    assert len(posts) == 2
    keys = {request.headers["Idempotency-Key"] for request in posts}
    assert len(keys) == 1 and keys.pop().startswith("rabbit-mcp-")
    assert sleeps[0] == 7.0  # waited the server's Retry-After
    assert all(r.headers["Authorization"] == "Bearer rk_test_fromenv" for r in seen)


def test_429_past_the_deadline_is_a_structured_error(monkeypatch):
    import httpx

    def handler(request):
        return httpx.Response(429, headers={"Retry-After": "30"}, json={
            "code": "too_many_in_flight_analyses", "detail": "busy", "fix_hint": "wait"})

    monkeypatch.setenv("RABBIT_MCP_POLL_TIMEOUT", "5")
    _mock_api(monkeypatch, handler)
    err = error(call("run_models", {"dataset_id": "ds_1"}))
    assert (err["code"], err["status"], err["retry_after"]) == (
        "too_many_in_flight_analyses", 429, "30")


@pytest.mark.parametrize("body", [["not", "an", "object"], "oops", None])
def test_non_object_error_bodies_are_structured_errors(monkeypatch, body):
    import httpx

    def handler(request):
        if body is None:
            return httpx.Response(502, text="<html>bad gateway</html>")
        return httpx.Response(500, json=body)

    _mock_api(monkeypatch, handler)
    for tool in ("run_models", "dataset_quality"):
        err = error(call(tool, {"dataset_id": "ds_1"}))
        assert err["code"] == "api_error" and err["status"] in (500, 502)


def test_non_object_success_body_is_a_structured_error(monkeypatch):
    import httpx

    _mock_api(monkeypatch, lambda request: httpx.Response(200, json=[1, 2]))
    err = error(call("dataset_quality", {"dataset_id": "ds_1"}))
    assert err["code"] == "api_error"


@pytest.mark.parametrize("url,allowed", [
    ("https://rabbit.example", True),
    ("http://localhost:8000", True),
    ("http://127.0.0.1:8000", True),
    ("http://[::1]:8000", True),
    ("http://rabbit.example", False),
    ("http://10.0.0.5:8000", False),
    ("http://localhost.evil.example", False),
    ("ftp://rabbit.example", False),
    ("rabbit.example", False),
])
def test_plain_http_api_url_only_for_loopback(monkeypatch, url, allowed):
    import httpx

    _mock_api(monkeypatch, lambda request: httpx.Response(200, json={
        "status": "ready", "touchpoint_count": 1, "unique_customers": 1, "validation": {}}))
    monkeypatch.setenv("RABBIT_URL", url)
    result = call("dataset_quality", {"dataset_id": "ds_1"})
    if allowed:
        ok(result)
    else:
        assert error(result)["code"] == "insecure_api_url"


def test_poll_timeout_cancels_the_analysis(v2_api, client, monkeypatch):
    client.app.state.analysis_inline_worker = False  # leave it queued
    monkeypatch.setenv("RABBIT_MCP_POLL_TIMEOUT", "0")
    try:
        err = error(call("run_models", {"dataset_id": v2_api, "models": ["linear"]}))
    finally:
        client.app.state.analysis_inline_worker = True
    assert err["code"] == "analysis_timeout" and err["cancelled"] is True
    key = os.environ["RABBIT_API_KEY"]
    analysis = client.get(f"/v2/analyses/{err['analysis_id']}",
                          headers={"Authorization": f"Bearer {key}"}).json()
    assert analysis["status"] == "cancelled"


def test_default_poll_timeout_is_sixty_seconds():
    assert rabbit_mcp.DEFAULT_POLL_TIMEOUT_SECONDS == 60


def test_dataset_quality_missing_file_is_a_tool_error():
    err = error(call("dataset_quality", {"touchpoints_path": "/nonexistent/rabbit/t.csv"}))
    assert err["code"] == "file_not_found"


def test_finished_during_cancel_returns_the_result(monkeypatch):
    """Poll times out while queued, cancel gets 409 because the analysis just
    finished; one re-fetch returns the succeeded result."""
    import httpx

    gets = []

    def handler(request):
        path = request.url.path
        if request.method == "POST" and path == "/v2/analyses":
            return httpx.Response(202, json={"id": "an_1", "status": "queued"})
        if request.method == "POST" and path.endswith("/cancel"):
            return httpx.Response(409, json={"code": "analysis_not_cancellable",
                                             "detail": "Analysis an_1 is succeeded."})
        gets.append(request)
        if len(gets) == 1:
            return httpx.Response(200, json={**SUCCEEDED, "status": "queued"})
        return httpx.Response(200, json=SUCCEEDED)

    monkeypatch.setenv("RABBIT_MCP_POLL_TIMEOUT", "0")
    _mock_api(monkeypatch, handler)
    body = ok(call("run_models", {"dataset_id": "ds_1", "models": ["linear"]}))
    assert body["source"]["analysis_id"] == "an_1"
    assert len(gets) == 2


def test_failed_during_cancel_reports_its_own_error(monkeypatch):
    import httpx

    gets = []

    def handler(request):
        if request.method == "POST" and request.url.path == "/v2/analyses":
            return httpx.Response(202, json={"id": "an_1", "status": "queued"})
        if request.url.path.endswith("/cancel"):
            return httpx.Response(409, json={"code": "analysis_not_cancellable", "detail": "x"})
        gets.append(request)
        if len(gets) == 1:
            return httpx.Response(200, json={**SUCCEEDED, "status": "running"})
        return httpx.Response(200, json={**SUCCEEDED, "status": "failed", "results": None,
                                         "error": {"code": "worker_timeout", "message": "w"}})

    monkeypatch.setenv("RABBIT_MCP_POLL_TIMEOUT", "0")
    _mock_api(monkeypatch, handler)
    assert error(call("run_models", {"dataset_id": "ds_1"}))["code"] == "worker_timeout"


@pytest.mark.parametrize("exc", ["ConnectError", "ReadTimeout", "ConnectTimeout",
                                 "RemoteProtocolError"])
def test_network_errors_are_api_unreachable(monkeypatch, exc):
    import httpx

    def handler(request):
        raise getattr(httpx, exc)("made-up network failure", request=request)

    _mock_api(monkeypatch, handler)
    for tool in ("run_models", "compare_models", "dataset_quality"):
        err = error(call(tool, {"dataset_id": "ds_1"}))
        assert err["code"] == "api_unreachable", (tool, err)
        assert exc in err["message"]


def test_unreachable_real_port_is_api_unreachable(monkeypatch):
    """No mock: a closed loopback port gives a real httpx ConnectError."""
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]  # closed once the block exits
    monkeypatch.setenv("RABBIT_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("RABBIT_API_KEY", "rk_test_fromenv")
    monkeypatch.setattr(rabbit_mcp, "API_CLIENT_FACTORY", None)
    assert error(call("dataset_quality", {"dataset_id": "ds_1"}))["code"] == "api_unreachable"
