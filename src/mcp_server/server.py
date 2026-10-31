"""rabbit-mcp: a local stdio MCP server over Rabbit's attribution engine (L2).

Four tools, all over existing code; nothing here computes a number itself.

- ``import_ga4``: the GA4 BigQuery importer (src/importers/ga4_bigquery.py),
  run locally on this machine's Application Default Credentials.
- ``run_models``: the five rule-based models (src/v2/analyses.py).
- ``compare_models``: the M3b Jensen-Shannon comparison (src/v2/comparison.py).
- ``dataset_quality``: the dataset validation used at upload (src/v2/datasets.py).

``run_models``, ``compare_models`` and ``dataset_quality`` take either a local
``touchpoints_path`` (run in this process) or a ``dataset_id`` already uploaded
to a Rabbit v2 API, reached at ``RABBIT_URL`` with ``RABBIT_API_KEY`` from the
environment. No tool accepts credentials as an argument.

Results go back to the MCP client, so they reach the model behind the user's
own agent. Every credit is an association under a named model, not causal impact.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import time
import uuid
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated, Any, Callable

import anyio
from mcp.server.fastmcp import FastMCP
from mcp.types import CallToolResult, TextContent, ToolAnnotations
from pydantic import Field

SERVER_NAME = "rabbit-mcp"
MEANING = (
    "Attribution credits are an association under the named model, not causal "
    "impact or incrementality; they do not say what would happen if spend changed."
)
FIVE_MODELS = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]
SUPPORTED_EXTENSIONS = {"csv", "json", "parquet"}
POLL_INTERVAL_SECONDS = 1.0
DEFAULT_POLL_TIMEOUT_SECONDS = 60
MAX_RETRY_AFTER_SECONDS = 30

# Test seams. None means: let the importer build its own ADC client, and talk
# to RABBIT_URL with a plain httpx client.
BIGQUERY_CLIENT_FACTORY: Callable[[], Any] | None = None
API_CLIENT_FACTORY: Callable[[str], Any] | None = None


class ToolFailure(Exception):
    """A structured, user-facing tool error."""

    def __init__(self, code: str, message: str, **details: Any):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


def _result(body: dict[str, Any], is_error: bool = False) -> CallToolResult:
    body = {**body, "meaning": MEANING}
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(body, default=str))],
        structuredContent=body,
        isError=is_error,
    )


def _error(failure: ToolFailure) -> CallToolResult:
    return _result(
        {"error": {"code": failure.code, "message": failure.message, **failure.details}},
        is_error=True,
    )


async def _guarded(work: Callable[[], dict[str, Any]]) -> CallToolResult:
    """Run blocking engine work off the event loop; map failures to tool errors.

    Engine prints are safe here: under stdio, ``main`` has already moved fd 1
    and ``sys.stdout`` to stderr (see ``_claim_stdout_for_protocol``).
    """
    try:
        return _result(await anyio.to_thread.run_sync(work))
    except ToolFailure as failure:
        return _error(failure)


def _from_problem(exc) -> ToolFailure:
    """An engine ApiProblem (the same 4xx the HTTP API returns) as a tool error."""
    return ToolFailure(exc.code, exc.detail, fix_hint=exc.fix_hint, status=exc.status)


# --- source resolution ---------------------------------------------------------


def _source(touchpoints_path: str | None, dataset_id: str | None) -> tuple[str, str]:
    if bool(touchpoints_path) == bool(dataset_id):
        raise ToolFailure(
            "invalid_source",
            "Pass exactly one of touchpoints_path (a local CSV, JSON or Parquet file) "
            "or dataset_id (a dataset already uploaded to the Rabbit v2 API).",
        )
    return ("file", touchpoints_path) if touchpoints_path else ("v2_api", dataset_id)


def _local_path(path_text: str) -> tuple[Path, str]:
    """Check a touchpoints path; returns the path and its extension."""
    path = Path(path_text).expanduser()
    if not path.is_file():
        raise ToolFailure("file_not_found", f"No file at {path_text!r}.",
                          fix_hint="Pass an absolute path to a touchpoints file.")
    extension = path.suffix.lower().lstrip(".")
    if extension not in SUPPORTED_EXTENSIONS:
        raise ToolFailure(
            "unsupported_file_type",
            f"{path.name} is not CSV, JSON or Parquet.",
            fix_hint="Use a touchpoints file with a .csv, .json or .parquet extension.",
        )
    return path, extension


def _read_local(path_text: str):
    from src.v2.datasets import _read_frame

    path, extension = _local_path(path_text)
    return path, _read_frame(path.read_bytes(), extension)


def _quality_report(frame) -> dict[str, Any]:
    from src.v2.datasets import _dropped_row_warnings, _validation_report

    report = _validation_report(frame)
    if not report.errors:
        report.warnings.extend(_dropped_row_warnings(frame))
    return report.model_dump()


def _ready_frame(path_text: str):
    from src.v2.analyses import MAX_ANALYSIS_TOUCHPOINTS

    path, frame = _read_local(path_text)
    report = _quality_report(frame)
    if report["errors"]:
        raise ToolFailure(
            "dataset_invalid",
            f"{path.name} failed validation; no model was run.",
            validation=report,
            fix_hint="Call dataset_quality for the full report, fix the file and retry.",
        )
    if len(frame) > MAX_ANALYSIS_TOUCHPOINTS:
        raise ToolFailure(
            "dataset_too_large",
            f"{path.name} has {len(frame)} touchpoints; analyses are limited to "
            f"{MAX_ANALYSIS_TOUCHPOINTS:,}.",
            fix_hint="Split the file into smaller date ranges.",
        )
    return path, frame


# --- v2 API --------------------------------------------------------------------


def _api_settings() -> tuple[str, str]:
    url, key = os.getenv("RABBIT_URL"), os.getenv("RABBIT_API_KEY")
    if not url or not key:
        raise ToolFailure(
            "api_not_configured",
            "dataset_id needs a Rabbit v2 API: set RABBIT_URL and RABBIT_API_KEY in the "
            "MCP server's environment, or pass touchpoints_path to run locally.",
        )
    _check_api_url(url)
    return url.rstrip("/"), key


def _check_api_url(url: str) -> None:
    """https anywhere; plain http only to this machine, so the key never crosses
    a network in clear text."""
    import ipaddress
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    host = (parts.hostname or "").lower()
    if parts.scheme == "https" and host:
        return
    if parts.scheme == "http" and host:
        try:
            loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = host == "localhost"
        if loopback:
            return
    raise ToolFailure(
        "insecure_api_url",
        f"RABBIT_URL must be https://, or http:// to localhost/127.0.0.1/::1; got {url!r}.",
        fix_hint="Put the Rabbit API behind TLS, or tunnel it to localhost.",
    )


def _api_client(base_url: str):
    if API_CLIENT_FACTORY is not None:
        return API_CLIENT_FACTORY(base_url)
    import httpx

    return httpx.Client(base_url=base_url, timeout=30.0)


def _api(client, method: str, path: str, key: str, headers: dict | None = None,
         **kwargs) -> dict[str, Any]:
    import httpx

    try:
        response = client.request(
            method, path, headers={**(headers or {}), "Authorization": f"Bearer {key}"},
            **kwargs,
        )
    except httpx.TransportError as exc:  # connect failures, timeouts, resets
        raise ToolFailure(
            "api_unreachable",
            f"Could not reach the Rabbit API for {method} {path}: {type(exc).__name__}.",
            fix_hint="Check RABBIT_URL and that the API is running.",
        ) from exc
    try:
        body = response.json()
    except ValueError:
        body = None
    if response.status_code >= 400:
        problem = body if isinstance(body, dict) else {}
        details: dict[str, Any] = {"status": response.status_code,
                                   "fix_hint": problem.get("fix_hint")}
        if response.headers.get("Retry-After"):
            details["retry_after"] = response.headers["Retry-After"]
        raise ToolFailure(
            str(problem.get("code") or "api_error"),
            str(problem.get("detail") or f"Rabbit API returned HTTP {response.status_code}."),
            **details,
        )
    if not isinstance(body, dict):
        raise ToolFailure("api_error", f"Rabbit API returned a non-object body for {path}.",
                          status=response.status_code)
    return body


def _retry_after_seconds(failure: ToolFailure) -> float:
    try:
        return max(1.0, min(float(failure.details.get("retry_after")), MAX_RETRY_AFTER_SECONDS))
    except (TypeError, ValueError):
        return POLL_INTERVAL_SECONDS


def _api_analysis(dataset_id: str, models: list[str], options: dict | None) -> dict[str, Any]:
    url, key = _api_settings()
    timeout = float(os.getenv("RABBIT_MCP_POLL_TIMEOUT", DEFAULT_POLL_TIMEOUT_SECONDS))
    payload: dict[str, Any] = {"dataset_id": dataset_id, "models": models}
    if options:
        payload["options"] = options
    # One key per tool call: a retried POST (after a 429) replays instead of
    # queueing a second analysis.
    headers = {"Idempotency-Key": f"rabbit-mcp-{uuid.uuid4()}"}
    deadline = time.monotonic() + timeout
    with _api_client(url) as client:
        while True:
            try:
                created = _api(client, "POST", "/v2/analyses", key, json=payload,
                               headers=headers)
                break
            except ToolFailure as failure:
                wait = _retry_after_seconds(failure)
                if failure.details.get("status") != 429 or time.monotonic() + wait > deadline:
                    raise
                time.sleep(wait)
        while True:
            analysis = _api(client, "GET", f"/v2/analyses/{created['id']}", key)
            if analysis["status"] in ("succeeded", "failed", "cancelled"):
                break
            if time.monotonic() > deadline:
                cancelled = True
                try:
                    _api(client, "POST", f"/v2/analyses/{created['id']}/cancel", key)
                except ToolFailure:
                    # Usually 409: it finished between the poll and the cancel.
                    # Look once more: a succeeded result is returned, and a
                    # failed one reports its own error below.
                    cancelled = False
                    final = _api(client, "GET", f"/v2/analyses/{created['id']}", key)
                    if final["status"] in ("succeeded", "failed", "cancelled"):
                        analysis = final
                        break
                raise ToolFailure(
                    "analysis_timeout",
                    f"Analysis {created['id']} was still {analysis['status']} after "
                    f"{timeout:.0f}s" + ("; it was cancelled." if cancelled else "."),
                    analysis_id=created["id"],
                    cancelled=cancelled,
                    fix_hint="Raise RABBIT_MCP_POLL_TIMEOUT, or check the API's worker.",
                )
            time.sleep(POLL_INTERVAL_SECONDS)
    if analysis["status"] != "succeeded":
        error = analysis.get("error") or {}
        raise ToolFailure(
            error.get("code") or f"analysis_{analysis['status']}",
            error.get("message") or f"Analysis {analysis['id']} ended {analysis['status']}.",
            analysis_id=analysis["id"],
        )
    return analysis


# --- engine calls ----------------------------------------------------------------


def _run_models(touchpoints_path, dataset_id, models, options) -> dict[str, Any]:
    from src.v2.analyses import (
        _interpretation,
        compute_model_result,
        resolve_parameters,
        validate_models,
    )
    from src.v2.auth.errors import ApiProblem
    from src.v2.comparison import build_comparison

    kind, value = _source(touchpoints_path, dataset_id)
    models = list(models) if models is not None else list(FIVE_MODELS)
    try:
        validate_models(models)
        parameters = {model: resolve_parameters(model, options) for model in models}
    except ApiProblem as exc:
        raise _from_problem(exc) from exc

    if kind == "v2_api":
        analysis = _api_analysis(value, models, options)
        return {
            "source": {"type": "v2_api", "dataset_id": value, "analysis_id": analysis["id"]},
            "models": analysis["models"],
            "summary": analysis["summary"],
            "results": analysis["results"],
            "comparison": analysis.get("comparison"),
            "interpretation": analysis["interpretation"],
        }

    path, frame = _ready_frame(value)
    summary, results = None, {}
    for model in models:
        try:
            summary, results[model] = compute_model_result(frame, model, parameters[model])
        except ValueError as exc:
            raise ToolFailure("analysis_failed", f"{model} could not run: {str(exc)[:300]}") from exc
    return {
        "source": {"type": "file", "path": str(path)},
        "models": models,
        "summary": summary,
        "results": results,
        "comparison": build_comparison(models, results),
        "interpretation": _interpretation(models),
    }


def _dataset_quality(touchpoints_path, dataset_id) -> dict[str, Any]:
    kind, value = _source(touchpoints_path, dataset_id)
    if kind == "v2_api":
        url, key = _api_settings()
        with _api_client(url) as client:
            dataset = _api(client, "GET", f"/v2/datasets/{value}", key)
        return {
            "source": {"type": "v2_api", "dataset_id": value},
            "status": dataset["status"],
            "touchpoint_count": dataset.get("touchpoint_count"),
            "unique_customers": dataset.get("unique_customers"),
            "validation": dataset.get("validation"),
        }
    from src.v2.datasets import _read_frame, _validation_report

    path, extension = _local_path(value)  # missing file or wrong type: a tool error
    try:
        frame = _read_frame(path.read_bytes(), extension)
    except Exception as exc:  # unparseable file: same report the upload gives
        report = _validation_report(None, exc).model_dump()
        return {"source": {"type": "file", "path": str(path)}, "status": "invalid",
                "touchpoint_count": None, "unique_customers": None, "validation": report}
    report = _quality_report(frame)
    return {
        "source": {"type": "file", "path": str(path)},
        "status": "invalid" if report["errors"] else "ready",
        "touchpoint_count": len(frame),
        "unique_customers": (
            int(frame["customer_id"].nunique()) if "customer_id" in frame else None
        ),
        "validation": report,
    }


_IMPORT_ERROR_CODES = {
    "InvalidArgument": "invalid_argument",
    "NoExportTables": "no_export_tables",
    "ByteLimitExceeded": "byte_limit_exceeded",
    "BytesBilledExceeded": "bytes_billed_exceeded",
    "AccessDenied": "access_denied",
    "BigQueryFailed": "bigquery_error",
}


def _output_path(out_path: str | None) -> Path:
    if out_path is None:
        handle, name = tempfile.mkstemp(prefix="rabbit-ga4-", suffix=".csv")
        os.close(handle)
        return Path(name)
    path = Path(out_path).expanduser()
    if not path.is_absolute():
        raise ToolFailure("invalid_argument", f"out_path must be absolute, got {out_path!r}.",
                          exit_code=2)
    if not path.parent.is_dir():
        raise ToolFailure("invalid_argument", f"Directory {str(path.parent)!r} does not exist.",
                          exit_code=2)
    if path.exists():
        raise ToolFailure("output_exists", f"{str(path)!r} already exists; nothing was queried.",
                          fix_hint="Pass a new out_path or omit it to use a temp file.")
    return path.resolve()


def _import_ga4(project, dataset, start, end, conversion_event, max_bytes, out_path):
    from src.importers import ga4_bigquery as ga4

    max_bytes = ga4.DEFAULT_MAX_BYTES if max_bytes is None else max_bytes
    try:
        ga4.validate_arguments(project, dataset, start, end, conversion_event)
        if max_bytes <= 0:
            raise ga4.InvalidArgument("max_bytes must be positive.")
    except ga4.ImportErrorBase as exc:
        raise ToolFailure("invalid_argument", str(exc), exit_code=exc.exit_code) from exc
    path = _output_path(out_path)
    estimate: dict[str, int] = {}
    try:
        result = ga4.import_ga4(
            project, dataset, start, end, conversion_event,
            max_bytes=max_bytes,
            client=BIGQUERY_CLIENT_FACTORY() if BIGQUERY_CLIENT_FACTORY else None,
            on_estimate=lambda estimated, tables: estimate.update(tables=tables),
        )
    except ga4.ImportErrorBase as exc:
        if out_path is None:
            path.unlink(missing_ok=True)
        details: dict[str, Any] = {"exit_code": exc.exit_code}
        if isinstance(exc, ga4.ByteLimitExceeded):
            details.update(estimated_bytes=exc.estimated, max_bytes=exc.max_bytes)
        raise ToolFailure(
            _IMPORT_ERROR_CODES.get(type(exc).__name__, "bigquery_error"), str(exc), **details
        ) from exc
    frame, stats = result.frame, result.stats
    frame.to_csv(path, index=False)
    tables = estimate.get("tables", 0)
    return {
        "csv_path": str(path),
        "touchpoints": len(frame),
        "session_starts": stats["session_starts"],
        "conversions": stats["conversions"],
        "customers": int(frame["customer_id"].nunique()),
        "source_rows": result.source_rows,
        "stats": stats,
        "estimated_bytes": result.estimated_bytes,
        "processed_bytes": result.processed_bytes,
        "max_bytes": max_bytes,
        "daily_tables": tables,
        "minimum_billed_bytes": tables * ga4.MIN_BILLED_BYTES_PER_TABLE,
        "channel_note": (
            "Untagged sessions take GA4's last non-direct session source, as in GA4's "
            "session source/medium, so direct is undercounted and a returning visitor's "
            "earlier source can repeat as a touch."
        ),
        "next": "Call run_models or compare_models with touchpoints_path set to csv_path.",
    }


# --- server ----------------------------------------------------------------------

_SOURCE_HELP = (
    "Give exactly one source: touchpoints_path (absolute path to a local CSV, JSON or "
    "Parquet touchpoints file, run in this process) or dataset_id (a dataset uploaded "
    "to the Rabbit v2 API at RABBIT_URL, using RABBIT_API_KEY from the server's environment). "
)
_MEANING_HELP = (
    " Credits describe association under the named model, not causal impact; numbers "
    "come only from Rabbit's engine."
)

TouchpointsPath = Annotated[
    str | None, Field(description="Absolute path to a local touchpoints CSV, JSON or Parquet file.")
]
DatasetId = Annotated[str | None, Field(description="A dataset id on the Rabbit v2 API.")]
Models = Annotated[
    list[str] | None,
    Field(description="1 to 5 of first_touch, last_touch, linear, time_decay, "
                      "position_based. Default: all five."),
]
Options = Annotated[
    dict[str, Any] | None,
    Field(description="Optional: time_decay_half_life_days (default 7), "
                      "position_based_weights {first, last} (default 0.4/0.4), "
                      "conversion_window_days."),
]


def build_server() -> FastMCP:
    server = FastMCP(SERVER_NAME, instructions=(
        "Rabbit runs five rule-based attribution models on marketing touchpoints. "
        "Quote numbers only from tool results, and name the model for every credit: "
        + MEANING
    ))

    @server.tool(
        description=(
            "Read one date range of a GA4 BigQuery export (events_*) into Rabbit touchpoints, "
            "read-only, with this machine's Application Default Credentials. Dry-runs first "
            "and refuses when the estimate exceeds max_bytes (default 10 GiB); the real query "
            "sets maximum_bytes_billed to max_bytes and bills the GCP project. Dates are "
            "YYYYMMDD. Writes a new touchpoints CSV to out_path (absolute, must not exist) or "
            "to a temp file, and returns its path with a summary." + _MEANING_HELP
        ),
        annotations=ToolAnnotations(title="Import GA4 from BigQuery", readOnlyHint=False,
                                    destructiveHint=False, idempotentHint=False,
                                    openWorldHint=True),
    )
    async def import_ga4(
        project: Annotated[str, Field(description="GCP project that holds the export.")],
        dataset: Annotated[str, Field(description="Export dataset, e.g. analytics_123456789.")],
        start: Annotated[str, Field(description="First export day, YYYYMMDD.")],
        end: Annotated[str, Field(description="Last export day, YYYYMMDD.")],
        conversion_event: Annotated[str, Field(description="GA4 event name, e.g. purchase.")],
        max_bytes: Annotated[int | None, Field(description="Refuse above this many bytes "
                                                           "(default 10737418240).")] = None,
        out_path: Annotated[str | None, Field(description="Absolute path for the CSV; must "
                                                          "not exist. Default: a temp file.")] = None,
    ) -> CallToolResult:
        return await _guarded(lambda: _import_ga4(
            project, dataset, start, end, conversion_event, max_bytes, out_path))

    @server.tool(
        description=(
            "Run Rabbit's rule-based attribution models (first_touch, last_touch, linear, "
            "time_decay, position_based) and return each channel's credit, conversions and "
            "revenue per model. " + _SOURCE_HELP + _MEANING_HELP
        ),
        annotations=ToolAnnotations(title="Run attribution models", readOnlyHint=True,
                                    destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
    )
    async def run_models(
        touchpoints_path: TouchpointsPath = None,
        dataset_id: DatasetId = None,
        models: Models = None,
        options: Options = None,
    ) -> CallToolResult:
        return await _guarded(lambda: _run_models(touchpoints_path, dataset_id, models, options))

    @server.tool(
        description=(
            "Compare two to five attribution models on one dataset: per-channel credit by "
            "model, the spread, and model_agreement_score (1 - mean pairwise Jensen-Shannon "
            "divergence, base 2). Agreement between models is not evidence that any model "
            "is correct. " + _SOURCE_HELP + _MEANING_HELP
        ),
        annotations=ToolAnnotations(title="Compare attribution models", readOnlyHint=True,
                                    destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
    )
    async def compare_models(
        touchpoints_path: TouchpointsPath = None,
        dataset_id: DatasetId = None,
        models: Models = None,
        options: Options = None,
    ) -> CallToolResult:
        def work():
            if models is not None and len(models) < 2:
                raise ToolFailure("validation_failed", "compare_models needs 2 to 5 models.",
                                  fix_hint="Omit models to compare all five.")
            body = _run_models(touchpoints_path, dataset_id, models, options)
            return {
                "source": body["source"],
                "models": body["models"],
                "comparison": body["comparison"],
                "interpretation": body["interpretation"],
            }

        return await _guarded(work)

    @server.tool(
        description=(
            "Check a touchpoints dataset with the same validation Rabbit runs at upload: "
            "required columns, data types, and rows that cannot become touchpoints. Returns "
            "status (ready or invalid), counts, errors and warnings. " + _SOURCE_HELP
            + "Run it before run_models." + _MEANING_HELP
        ),
        annotations=ToolAnnotations(title="Check dataset quality", readOnlyHint=True,
                                    destructiveHint=False, idempotentHint=True,
                                    openWorldHint=False),
    )
    async def dataset_quality(
        touchpoints_path: TouchpointsPath = None,
        dataset_id: DatasetId = None,
    ) -> CallToolResult:
        return await _guarded(lambda: _dataset_quality(touchpoints_path, dataset_id))

    return server


def _claim_stdout_for_protocol() -> anyio.AsyncFile[str]:
    """Reserve the real stdout for JSON-RPC and send everything else to stderr.

    The engine prints diagnostics (for example the journey builder's
    "Error creating touchpoint" lines) from worker threads. A per-call
    ``redirect_stdout`` swaps process-global state and races between
    concurrent calls, so instead, once at startup: duplicate fd 1 for the
    protocol, point fd 1 at stderr (catches C-level and subprocess writes),
    and point ``sys.stdout`` at stderr (catches ``print``).
    """
    sys.stdout.flush()
    protocol = os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)
    sys.stdout = sys.stderr
    return anyio.wrap_file(TextIOWrapper(protocol, encoding="utf-8"))


async def _serve_stdio(server: FastMCP, protocol_out: anyio.AsyncFile[str]) -> None:
    from mcp.server.stdio import stdio_server

    # FastMCP.run_stdio_async, but with the reserved protocol stream.
    lowlevel = server._mcp_server
    async with stdio_server(stdout=protocol_out) as (read_stream, write_stream):
        await lowlevel.run(read_stream, write_stream, lowlevel.create_initialization_options())


def main() -> None:
    server = build_server()
    protocol_out = _claim_stdout_for_protocol()
    anyio.run(_serve_stdio, server, protocol_out)


if __name__ == "__main__":  # pragma: no cover
    main()
