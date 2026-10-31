"""Read-only importer for the standard GA4 BigQuery export (``events_*``).

Reads one date range of a GA4 export dataset and returns a touchpoint table in
the same columns as Rabbit's CSV upload format, so the existing dataset
validation and all five attribution models run on it unchanged. Credits those
models produce describe association under the named model, not causal impact.

Safety and cost:

- Only one statement is ever sent: the SELECT built by :func:`build_query`.
  No DDL, DML, scripts or temporary tables.
- Every run dry-runs the query first and refuses to continue when the estimate
  exceeds ``max_bytes``. The real query also sets ``maximum_bytes_billed`` to
  ``max_bytes``, so BigQuery itself rejects it if the estimate was wrong.
- Credentials come from Application Default Credentials on the machine that
  runs the importer, requested with :data:`READONLY_SCOPE`. They are never
  accepted as arguments, stored or logged.

Field mapping is documented in docs/importers/ga4-bigquery.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

import pandas as pd

# The narrowest OAuth scope that the BigQuery v2 API accepts for jobs.query,
# jobs.getQueryResults, jobs.get, tables.get and tables.list (BigQuery v2
# discovery document, revision 20240919). ``bigquery.readonly`` is not listed
# for any of those methods, and jobs.insert needs a read-write scope, so the
# importer sends queries through jobs.query only.
READONLY_SCOPE = "https://www.googleapis.com/auth/cloud-platform.read-only"
SCOPES = (READONLY_SCOPE,)

DEFAULT_MAX_BYTES = 10 * 1024**3  # 10 GiB
TOUCHPOINT_COLUMNS = [
    "timestamp",
    "channel",
    "event_type",
    "customer_id",
    "session_id",
    "campaign_id",
    "conversion_value",
]
SESSION_EVENT = "session_start"
DIRECT = "direct"
# Values GA4 writes when it has no source/medium/campaign; all map to missing.
UNSET_VALUES = {"", "(not set)", "(none)", "(direct)", "(not provided)", "null"}

_PROJECT_RE = re.compile(r"^[a-z][a-z0-9.:-]{4,61}[a-z0-9]$")
_DATASET_RE = re.compile(r"^[A-Za-z0-9_]{1,1024}$")
_EVENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
_DATE_RE = re.compile(r"^\d{8}$")
_TABLE_RE = re.compile(r"^events_(\d{8})$")


class ImportErrorBase(Exception):
    """Base class for importer errors with a user-facing message."""


class InvalidArgument(ImportErrorBase):
    pass


class ByteLimitExceeded(ImportErrorBase):
    def __init__(self, estimated: int, max_bytes: int):
        self.estimated = estimated
        self.max_bytes = max_bytes
        super().__init__(
            f"Dry run estimates {format_bytes(estimated)} ({estimated} bytes), above "
            f"--max-bytes {format_bytes(max_bytes)} ({max_bytes} bytes). Nothing was "
            "queried. Narrow --start/--end or raise --max-bytes."
        )


class NoExportTables(ImportErrorBase):
    pass


@dataclass
class ImportResult:
    """Touchpoints plus what the run cost and what it saw."""

    frame: pd.DataFrame
    estimated_bytes: int
    processed_bytes: int | None
    source_rows: int
    stats: dict[str, int] = field(default_factory=dict)


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.2f} {unit}"
        size /= 1024
    return f"{value} B"


def validate_arguments(project: str, dataset: str, start: str, end: str, conversion_event: str):
    if not _PROJECT_RE.match(project or ""):
        raise InvalidArgument(f"Invalid GCP project id: {project!r}.")
    if not _DATASET_RE.match(dataset or ""):
        raise InvalidArgument(f"Invalid BigQuery dataset id: {dataset!r}.")
    for name, value in (("start", start), ("end", end)):
        if not _DATE_RE.match(value or ""):
            raise InvalidArgument(f"--{name} must be YYYYMMDD, got {value!r}.")
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError as exc:
            raise InvalidArgument(f"--{name} is not a real date: {value!r}.") from exc
    if start > end:
        raise InvalidArgument(f"--start {start} is after --end {end}.")
    if not _EVENT_RE.match(conversion_event or ""):
        raise InvalidArgument(f"Invalid GA4 event name: {conversion_event!r}.")


def build_query(project: str, dataset: str, columns: Iterable[str]) -> str:
    """The single SELECT the importer runs.

    ``columns`` are the top-level export columns to read; only those are
    scanned, which keeps bytes billed down. Dates and the conversion event are
    query parameters (@start, @end, @conversion_event); the table name cannot
    be a parameter, so project and dataset are validated before they get here.
    ``_TABLE_SUFFIX BETWEEN`` prunes the scan to the requested daily tables and
    excludes ``events_intraday_*``.
    """
    if not _PROJECT_RE.match(project) or not _DATASET_RE.match(dataset):
        raise InvalidArgument("Invalid project or dataset id.")
    select = ",\n  ".join(columns)
    return (
        f"SELECT\n  {select}\n"
        f"FROM `{project}.{dataset}.events_*`\n"
        "WHERE _TABLE_SUFFIX BETWEEN @start AND @end\n"
        f"  AND event_name IN ('{SESSION_EVENT}', @conversion_event)\n"
        "ORDER BY user_pseudo_id, event_timestamp"
    )


BASE_COLUMNS = ["event_timestamp", "event_name", "user_pseudo_id", "user_id", "event_params"]
OPTIONAL_COLUMNS = ["collected_traffic_source", "session_traffic_source_last_click", "ecommerce"]


# ---------------------------------------------------------------------------
# Row mapping (pure; tested against recorded export rows)
# ---------------------------------------------------------------------------


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return None if text.lower() in UNSET_VALUES else text


def event_param(row: Mapping[str, Any], key: str) -> Any:
    """Value of one GA4 event parameter (string, int, double or float)."""
    for param in row.get("event_params") or []:
        if param.get("key") != key:
            continue
        value = param.get("value") or {}
        for kind in ("string_value", "int_value", "double_value", "float_value"):
            if value.get(kind) is not None:
                return value[kind]
        return None
    return None


def traffic_source(row: Mapping[str, Any]) -> tuple[str | None, str | None, str | None, str]:
    """(source, medium, campaign, field used), checked in documented order."""
    collected = row.get("collected_traffic_source") or {}
    source = _clean(collected.get("manual_source"))
    if source:
        return (
            source,
            _clean(collected.get("manual_medium")),
            _clean(collected.get("manual_campaign_name")),
            "collected_traffic_source",
        )
    last_click = (row.get("session_traffic_source_last_click") or {}).get("manual_campaign") or {}
    source = _clean(last_click.get("source"))
    if source:
        return (
            source,
            _clean(last_click.get("medium")),
            _clean(last_click.get("campaign_name")),
            "session_traffic_source_last_click",
        )
    source = _clean(event_param(row, "source"))
    if source:
        return (
            source,
            _clean(event_param(row, "medium")),
            _clean(event_param(row, "campaign")),
            "event_params",
        )
    return None, None, None, DIRECT


def channel_name(source: str | None, medium: str | None) -> str:
    if not source:
        return DIRECT
    source = source.lower()
    return f"{source} / {medium.lower()}" if medium else source


def conversion_value(row: Mapping[str, Any]) -> float | None:
    revenue = (row.get("ecommerce") or {}).get("purchase_revenue")
    if revenue is None or pd.isna(revenue):
        revenue = event_param(row, "value")
    if revenue is None:
        return None
    try:
        number = float(revenue)
    except (TypeError, ValueError):
        return None
    return number if number >= 0 and number == number else None


def _timestamp(micros: Any) -> str:
    moment = datetime.fromtimestamp(int(micros) / 1_000_000, tz=timezone.utc)
    return moment.strftime("%Y-%m-%d %H:%M:%S.%f")


def rows_to_touchpoints(
    rows: Iterable[Mapping[str, Any]], conversion_event: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Map GA4 export rows to Rabbit touchpoints.

    One touchpoint per ``session_start`` (event_type ``view``) and one per
    conversion event (event_type ``conversion``). A device's rows join the
    journey of its ``user_id`` when any of its rows carries one; otherwise
    ``user_pseudo_id`` is the customer id.
    """
    rows = [dict(row.items()) if hasattr(row, "items") else dict(row) for row in rows]
    rows.sort(key=lambda r: (str(r.get("user_pseudo_id")), int(r.get("event_timestamp") or 0)))
    pseudo_to_user: dict[str, str] = {}
    for row in rows:
        user_id = _clean(row.get("user_id"))
        pseudo = _clean(row.get("user_pseudo_id"))
        if user_id and pseudo and pseudo not in pseudo_to_user:
            pseudo_to_user[pseudo] = user_id

    stats = {
        "session_starts": 0,
        "conversions": 0,
        "skipped_no_identity": 0,
        "skipped_other_event": 0,
        "channel_from_collected_traffic_source": 0,
        "channel_from_session_traffic_source_last_click": 0,
        "channel_from_event_params": 0,
        "channel_direct": 0,
    }
    records = []
    for row in rows:
        name = row.get("event_name")
        if name == conversion_event:
            event_type = "conversion"
        elif name == SESSION_EVENT:
            event_type = "view"
        else:
            stats["skipped_other_event"] += 1
            continue
        pseudo = _clean(row.get("user_pseudo_id"))
        customer = _clean(row.get("user_id")) or pseudo_to_user.get(pseudo or "") or pseudo
        if not customer or row.get("event_timestamp") is None:
            stats["skipped_no_identity"] += 1
            continue
        source, medium, campaign, used = traffic_source(row)
        stats[f"channel_{'direct' if used == DIRECT else 'from_' + used}"] += 1
        session_number = event_param(row, "ga_session_id")
        records.append(
            {
                "timestamp": _timestamp(row["event_timestamp"]),
                "channel": channel_name(source, medium),
                "event_type": event_type,
                "customer_id": customer,
                "session_id": f"{pseudo}.{session_number}" if session_number is not None else None,
                "campaign_id": campaign,
                "conversion_value": conversion_value(row) if event_type == "conversion" else None,
            }
        )
        stats["conversions" if event_type == "conversion" else "session_starts"] += 1
    frame = pd.DataFrame.from_records(records, columns=TOUCHPOINT_COLUMNS)
    frame = frame.sort_values(["customer_id", "timestamp"], kind="stable").reset_index(drop=True)
    return frame, stats


# ---------------------------------------------------------------------------
# BigQuery access
# ---------------------------------------------------------------------------


def make_client(project: str):
    """BigQuery client on Application Default Credentials, read-only scope.

    ``project`` is the billing project for query jobs. Credentials are never
    read from arguments or printed.
    """
    import google.auth
    from google.cloud import bigquery

    credentials, _ = google.auth.default(scopes=list(SCOPES))
    return bigquery.Client(project=project, credentials=credentials)


def _available_columns(client, project: str, dataset: str, start: str, end: str) -> list[str]:
    """Columns to select, from the newest daily table in range.

    Wildcard queries use the schema of the newest matching table, so optional
    columns (added to the export in 2023-2024) are selected only when it has
    them.
    """
    suffixes = sorted(
        match.group(1)
        for table in client.list_tables(f"{project}.{dataset}")
        if (match := _TABLE_RE.match(table.table_id)) and start <= match.group(1) <= end
    )
    if not suffixes:
        raise NoExportTables(
            f"No events_YYYYMMDD tables between {start} and {end} in {project}.{dataset}."
        )
    schema = client.get_table(f"{project}.{dataset}.events_{suffixes[-1]}").schema
    names = {column.name for column in schema}
    missing = [name for name in BASE_COLUMNS if name not in names]
    if missing:
        raise NoExportTables(
            f"events_{suffixes[-1]} is missing GA4 export columns: {', '.join(missing)}."
        )
    return BASE_COLUMNS + [name for name in OPTIONAL_COLUMNS if name in names]


def _job_config(start: str, end: str, conversion_event: str, *, dry_run: bool, max_bytes: int):
    from google.cloud import bigquery

    return bigquery.QueryJobConfig(
        dry_run=dry_run,
        use_query_cache=not dry_run,
        maximum_bytes_billed=None if dry_run else max_bytes,
        query_parameters=[
            bigquery.ScalarQueryParameter("start", "STRING", start),
            bigquery.ScalarQueryParameter("end", "STRING", end),
            bigquery.ScalarQueryParameter("conversion_event", "STRING", conversion_event),
        ],
    )


def import_ga4(
    project: str,
    dataset: str,
    start: str,
    end: str,
    conversion_event: str = "purchase",
    *,
    max_bytes: int = DEFAULT_MAX_BYTES,
    billing_project: str | None = None,
    client=None,
    on_estimate: Callable[[int, str], None] | None = None,
) -> ImportResult:
    """Import one date range of a GA4 export as Rabbit touchpoints.

    Function entry point for the CLI, the v2 API and a future MCP server.
    Dry-runs first and raises :class:`ByteLimitExceeded` before running
    anything billable when the estimate is above ``max_bytes``.
    ``on_estimate(bytes, sql)`` is called with the dry-run result.
    """
    validate_arguments(project, dataset, start, end, conversion_event)
    if max_bytes <= 0:
        raise InvalidArgument("--max-bytes must be positive.")
    client = client or make_client(billing_project or project)
    columns = _available_columns(client, project, dataset, start, end)
    sql = build_query(project, dataset, columns)

    dry = client.query(
        sql,
        job_config=_job_config(start, end, conversion_event, dry_run=True, max_bytes=max_bytes),
        api_method="QUERY",
    )
    estimated = int(dry.total_bytes_processed or 0)
    if on_estimate:
        on_estimate(estimated, sql)
    if estimated > max_bytes:
        raise ByteLimitExceeded(estimated, max_bytes)

    job = client.query(
        sql,
        job_config=_job_config(start, end, conversion_event, dry_run=False, max_bytes=max_bytes),
        api_method="QUERY",
    )
    rows = list(job.result())
    frame, stats = rows_to_touchpoints(rows, conversion_event)
    processed = getattr(job, "total_bytes_processed", None)
    return ImportResult(
        frame=frame,
        estimated_bytes=estimated,
        processed_bytes=int(processed) if isinstance(processed, int) else None,
        source_rows=len(rows),
        stats=stats,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.importers.ga4_bigquery",
        description=(
            "Read a GA4 BigQuery export (read-only) into Rabbit's touchpoint CSV. "
            "Queries bill the GCP project you run them in; a dry run checks the "
            "estimate against --max-bytes first."
        ),
    )
    parser.add_argument("--project", required=True, help="GCP project that holds the export")
    parser.add_argument("--dataset", required=True, help="GA4 export dataset, e.g. analytics_123456789")
    parser.add_argument("--start", required=True, help="first export day, YYYYMMDD")
    parser.add_argument("--end", required=True, help="last export day, YYYYMMDD")
    parser.add_argument("--conversion-event", required=True, help="GA4 event name, e.g. purchase")
    parser.add_argument("--out", help="write touchpoints CSV here (default: stdout)")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"refuse to run above this many bytes; sets maximum_bytes_billed (default {DEFAULT_MAX_BYTES}, 10 GiB)",
    )
    parser.add_argument("--billing-project", help="project billed for the query (default: --project)")
    return parser


def main(argv: list[str] | None = None, *, client=None) -> int:
    args = _parser().parse_args(argv)
    err = sys.stderr

    def report_estimate(estimated: int, _sql: str):
        print(
            f"Dry run: this query will process {format_bytes(estimated)} ({estimated} bytes); "
            f"limit --max-bytes {format_bytes(args.max_bytes)}.",
            file=err,
        )

    try:
        result = import_ga4(
            args.project,
            args.dataset,
            args.start,
            args.end,
            args.conversion_event,
            max_bytes=args.max_bytes,
            billing_project=args.billing_project,
            client=client,
            on_estimate=report_estimate,
        )
    except ByteLimitExceeded as exc:
        print(f"Refused: {exc}", file=err)
        return 3
    except ImportErrorBase as exc:
        print(f"Error: {exc}", file=err)
        return 2

    frame, stats = result.frame, result.stats
    print(
        f"Read {result.source_rows} export rows: {stats['session_starts']} session_start "
        f"touchpoints and {stats['conversions']} '{args.conversion_event}' conversions "
        f"for {frame['customer_id'].nunique()} customers.",
        file=err,
    )
    print(
        "Channel source: "
        f"{stats['channel_from_collected_traffic_source']} collected_traffic_source, "
        f"{stats['channel_from_session_traffic_source_last_click']} session_traffic_source_last_click, "
        f"{stats['channel_from_event_params']} event params, "
        f"{stats['channel_direct']} direct ((not set) or null).",
        file=err,
    )
    if args.out:
        frame.to_csv(args.out, index=False)
        print(f"Wrote {len(frame)} touchpoints to {args.out}.", file=err)
    else:
        frame.to_csv(sys.stdout, index=False)
    print(
        "Run any model on this file; its credits describe association under the "
        "named model, not causal impact.",
        file=err,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
