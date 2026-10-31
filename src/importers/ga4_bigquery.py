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
  runs the importer, requested with a read-only scope. They are never accepted
  as arguments, stored or logged.

Channel follows GA4's own session source/medium: a session's UTM tags, then a
gclid, then GA4's last non-direct click. Field mapping and limits are
documented in docs/importers/ga4-bigquery.md.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, Mapping

import pandas as pd

# OAuth scopes. The BigQuery v2 discovery document (revision 20260811) lists
# cloud-platform.read-only as the narrowest scope for jobs.query,
# jobs.getQueryResults, jobs.get, tables.get and tables.list; it does not list
# bigquery.readonly for any of them, and jobs.insert needs a read-write scope,
# so queries go through jobs.query only. Third-party reports say
# bigquery.readonly works for queries in practice; it is selectable with
# --oauth-scope so the first live run can check it.
CLOUD_PLATFORM_READONLY = "https://www.googleapis.com/auth/cloud-platform.read-only"
BIGQUERY_READONLY = "https://www.googleapis.com/auth/bigquery.readonly"
SCOPE_CHOICES = {
    "cloud-platform.read-only": CLOUD_PLATFORM_READONLY,
    "bigquery.readonly": BIGQUERY_READONLY,
}
READONLY_SCOPE = CLOUD_PLATFORM_READONLY
SCOPES = (READONLY_SCOPE,)

DEFAULT_MAX_BYTES = 10 * 1024**3  # 10 GiB
# On-demand pricing bills at least 10 MB per table a query references.
MIN_BILLED_BYTES_PER_TABLE = 10 * 1024**2
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

_PROJECT_RE = re.compile(r"[a-z][a-z0-9.:-]{4,61}[a-z0-9]")
_DATASET_RE = re.compile(r"[A-Za-z0-9_]{1,1024}")
_EVENT_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{0,39}")
_DATE_RE = re.compile(r"\d{8}")
_DAILY_TABLE_RE = re.compile(r"events_(\d{8})")
_WILDCARD_TABLE_RE = re.compile(r"events_(?:intraday_)?\d{8}")

# Exit codes for the CLI (documented in docs/importers/ga4-bigquery.md).
EXIT_OK = 0
EXIT_INVALID = 2
EXIT_REFUSED = 3
EXIT_BYTES_BILLED = 4
EXIT_ACCESS = 5
EXIT_BIGQUERY = 6


class ImportErrorBase(Exception):
    """Base class for importer errors with a user-facing message."""

    exit_code = EXIT_BIGQUERY


class InvalidArgument(ImportErrorBase):
    exit_code = EXIT_INVALID


class NoExportTables(ImportErrorBase):
    exit_code = EXIT_INVALID


class ByteLimitExceeded(ImportErrorBase):
    exit_code = EXIT_REFUSED

    def __init__(self, estimated: int, max_bytes: int):
        self.estimated = estimated
        self.max_bytes = max_bytes
        super().__init__(
            f"Dry run estimates {format_bytes(estimated)} ({estimated} bytes), above "
            f"--max-bytes {format_bytes(max_bytes)} ({max_bytes} bytes). Nothing was "
            "queried. Narrow --start/--end or raise --max-bytes."
        )


class BytesBilledExceeded(ImportErrorBase):
    """BigQuery refused the real query because of maximum_bytes_billed."""

    exit_code = EXIT_BYTES_BILLED


class AccessDenied(ImportErrorBase):
    """No usable credentials, or the account lacks a role or scope."""

    exit_code = EXIT_ACCESS


class BigQueryFailed(ImportErrorBase):
    """Any other BigQuery API error, including a dry run with no estimate."""

    exit_code = EXIT_BIGQUERY


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
    if not _PROJECT_RE.fullmatch(project or ""):
        raise InvalidArgument(f"Invalid GCP project id: {project!r}.")
    if not _DATASET_RE.fullmatch(dataset or ""):
        raise InvalidArgument(f"Invalid BigQuery dataset id: {dataset!r}.")
    for name, value in (("start", start), ("end", end)):
        if not _DATE_RE.fullmatch(value or ""):
            raise InvalidArgument(f"--{name} must be YYYYMMDD, got {value!r}.")
        try:
            datetime.strptime(value, "%Y%m%d")
        except ValueError as exc:
            raise InvalidArgument(f"--{name} is not a real date: {value!r}.") from exc
    if start > end:
        raise InvalidArgument(f"--start {start} is after --end {end}.")
    if not _EVENT_RE.fullmatch(conversion_event or ""):
        raise InvalidArgument(f"Invalid GA4 event name: {conversion_event!r}.")
    if conversion_event == SESSION_EVENT:
        raise InvalidArgument(
            f"--conversion-event cannot be {SESSION_EVENT}; it is read as the session touchpoint."
        )


def build_query(project: str, dataset: str, columns: Iterable[str]) -> str:
    """The single SELECT the importer runs.

    ``columns`` are the top-level export columns to read; only those are
    scanned, which keeps bytes billed down. Dates and the conversion event are
    query parameters (@start, @end, @conversion_event); the table name cannot
    be a parameter, so project and dataset are validated before they get here.
    ``_TABLE_SUFFIX BETWEEN`` prunes the scan to the requested daily tables and
    excludes ``events_intraday_*``.
    """
    if not _PROJECT_RE.fullmatch(project) or not _DATASET_RE.fullmatch(dataset):
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
# Row mapping (pure; tested against GA4-shaped fixture rows)
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


def _get(record: Any, key: str) -> Any:
    return record.get(key) if isinstance(record, Mapping) else None


def event_param(row: Mapping[str, Any], key: str) -> Any:
    """Value of one GA4 event parameter (string, int, double or float)."""
    for param in row.get("event_params") or []:
        if _get(param, "key") != key:
            continue
        value = _get(param, "value") or {}
        for kind in ("string_value", "int_value", "double_value", "float_value"):
            if value.get(kind) is not None:
                return value[kind]
        return None
    return None


# Where a touchpoint's channel came from, in precedence order.
SOURCE_UTM = "collected_utm"
SOURCE_GCLID = "collected_gclid"
SOURCE_LAST_CLICK = "last_non_direct_click"
SOURCE_EVENT_PARAMS = "event_params"


def traffic_source(row: Mapping[str, Any]) -> tuple[str | None, str | None, str | None, str]:
    """(source, medium, campaign, rule used) for one session event.

    Matches GA4's session source/medium:

    1. ``collected_traffic_source.manual_*``: the UTM tags on this event.
    2. ``collected_traffic_source.gclid`` with no UTM source: Google Ads
       auto-tagging, so ``google / cpc``, with the campaign name from
       ``session_traffic_source_last_click.google_ads_campaign``.
    3. ``session_traffic_source_last_click``: GA4's last non-direct click,
       which is how GA4 itself credits untagged organic, referral and direct
       sessions, so a direct visit after an earlier tagged one inherits that
       earlier source. Read from ``cross_channel_campaign`` (in the export
       from October 2024); when that has no source, from ``manual_campaign``,
       then ``google_ads_campaign`` as ``google / cpc`` (rows from July to
       October 2024 have only those two).
    4. Event params ``source``/``medium``/``campaign``, only when the row has
       no ``session_traffic_source_last_click`` at all (exported before July
       2024).
    5. Otherwise ``direct``. ``(not set)``, ``(none)``, ``(direct)`` and null
       count as no source at every step.
    """
    collected = row.get("collected_traffic_source") or {}
    last_click = row.get("session_traffic_source_last_click")
    source = _clean(collected.get("manual_source"))
    if source:
        return (
            source,
            _clean(collected.get("manual_medium")),
            _clean(collected.get("manual_campaign_name")),
            SOURCE_UTM,
        )
    if _clean(collected.get("gclid")):
        ads = _get(last_click, "google_ads_campaign") or {}
        return "google", "cpc", _clean(ads.get("campaign_name")), SOURCE_GCLID
    if last_click:
        for record in ("cross_channel_campaign", "manual_campaign"):
            campaign = last_click.get(record) or {}
            source = _clean(campaign.get("source"))
            if source:
                return (
                    source,
                    _clean(campaign.get("medium")),
                    _clean(campaign.get("campaign_name")),
                    SOURCE_LAST_CLICK,
                )
        ads = last_click.get("google_ads_campaign") or {}
        if any(_clean(ads.get(key)) for key in ("campaign_id", "campaign_name", "customer_id")):
            return "google", "cpc", _clean(ads.get("campaign_name")), SOURCE_LAST_CLICK
        return None, None, None, DIRECT
    source = _clean(event_param(row, "source"))
    if source:
        return (
            source,
            _clean(event_param(row, "medium")),
            _clean(event_param(row, "campaign")),
            SOURCE_EVENT_PARAMS,
        )
    return None, None, None, DIRECT


def channel_name(source: str | None, medium: str | None) -> str:
    if not source:
        return DIRECT
    source = source.lower()
    return f"{source} / {medium.lower()}" if medium else source


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def conversion_value(row: Mapping[str, Any]) -> float | None:
    """``purchase_revenue_in_usd``, else ``purchase_revenue``, else ``value``.

    The USD field keeps one currency across a multi-currency property. The two
    fallbacks are in the event's own currency. Negative values become None so
    the conversion still counts.
    """
    ecommerce = row.get("ecommerce") or {}
    for candidate in (
        ecommerce.get("purchase_revenue_in_usd"),
        ecommerce.get("purchase_revenue"),
        event_param(row, "value"),
    ):
        number = _number(candidate)
        if number is not None:
            return number if number >= 0 else None
    return None


def _timestamp(micros: Any) -> str:
    moment = datetime.fromtimestamp(int(micros) / 1_000_000, tz=timezone.utc)
    return moment.strftime("%Y-%m-%d %H:%M:%S.%f")


def _as_dict(row: Any) -> dict[str, Any]:
    """A plain dict from a BigQuery Row (or a dict)."""
    return dict(row.items())


def rows_to_touchpoints(
    rows: Iterable[Any], conversion_event: str
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Map GA4 export rows to Rabbit touchpoints.

    One touchpoint per ``session_start`` (event_type ``view``) and one per
    conversion event (event_type ``conversion``). A device's rows join the
    journey of its ``user_id`` when any of its rows carries one
    (``customer_id`` ``user:<user_id>``); otherwise the customer id is
    ``ga4:<user_pseudo_id>``. Rows with neither (for example
    consent-denied cookieless pings) are skipped and counted.
    """
    rows = [_as_dict(row) for row in rows]
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
        f"channel_from_{SOURCE_UTM}": 0,
        f"channel_from_{SOURCE_GCLID}": 0,
        f"channel_from_{SOURCE_LAST_CLICK}": 0,
        f"channel_from_{SOURCE_EVENT_PARAMS}": 0,
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
        user_id = _clean(row.get("user_id")) or pseudo_to_user.get(pseudo or "")
        # Prefixed so ids stay strings: GA4 pseudo ids look like numbers
        # ("1234567890.1709280000") and a CSV of only those would parse as floats.
        customer = f"user:{user_id}" if user_id else (f"ga4:{pseudo}" if pseudo else None)
        if not customer or row.get("event_timestamp") is None:
            stats["skipped_no_identity"] += 1
            continue
        source, medium, campaign, used = traffic_source(row)
        stats["channel_direct" if used == DIRECT else f"channel_from_{used}"] += 1
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


def make_client(project: str, scope: str = READONLY_SCOPE):
    """BigQuery client on Application Default Credentials, read-only scope.

    ``project`` is the billing project for query jobs. Credentials are never
    read from arguments or printed.
    """
    import google.auth
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud import bigquery

    if scope not in SCOPE_CHOICES.values():
        raise InvalidArgument(f"Unsupported OAuth scope: {scope!r}.")
    try:
        credentials, _ = google.auth.default(scopes=[scope])
    except DefaultCredentialsError as exc:
        raise AccessDenied(
            "No Application Default Credentials found. Run "
            "`gcloud auth application-default login` or set GOOGLE_APPLICATION_CREDENTIALS."
        ) from exc
    return bigquery.Client(project=project, credentials=credentials)


def _translate(exc: Exception) -> ImportErrorBase:
    """Map a Google API error to an importer error without echoing secrets."""
    from google.api_core import exceptions as gexc

    reasons = {str(e.get("reason", "")) for e in (getattr(exc, "errors", None) or [])
               if isinstance(e, Mapping)}
    message = str(getattr(exc, "message", "") or exc)[:500]
    if "bytesBilledLimitExceeded" in reasons or "bytes billed" in message.lower():
        return BytesBilledExceeded(
            f"BigQuery refused the query: it would bill more than --max-bytes. {message}"
        )
    if isinstance(exc, (gexc.Forbidden, gexc.Unauthorized)) or "accessDenied" in reasons:
        return AccessDenied(
            "BigQuery denied access. The account needs BigQuery Data Viewer on the "
            f"dataset and BigQuery Job User on the billing project. {message}"
        )
    if isinstance(exc, gexc.NotFound):
        return NoExportTables(f"Not found: {message}")
    return BigQueryFailed(f"BigQuery error: {message}")


def _available_columns(
    client, project: str, dataset: str, start: str, end: str
) -> tuple[list[str], int]:
    """Columns to select, from the table whose schema the wildcard will use.

    A wildcard query over ``events_*`` takes its schema from the most recently
    created table that matches the wildcard, which can be an
    ``events_intraday_*`` table or a day outside the requested range. Optional
    columns (added to the export in 2023-2024) are selected only when that
    table has them; daily tables in range must also exist. Returns the columns
    and the number of daily tables in range.
    """
    tables = list(client.list_tables(f"{project}.{dataset}"))
    in_range = [
        match.group(1)
        for table in tables
        if (match := _DAILY_TABLE_RE.fullmatch(table.table_id)) and start <= match.group(1) <= end
    ]
    if not in_range:
        raise NoExportTables(
            f"No events_YYYYMMDD tables between {start} and {end} in {project}.{dataset}."
        )
    matching = [table for table in tables if _WILDCARD_TABLE_RE.fullmatch(table.table_id)]

    def newest(table):
        created = getattr(table, "created", None)
        return (created.timestamp() if created else 0.0, table.table_id.rsplit("_", 1)[-1])

    schema_table = max(matching, key=newest).table_id
    schema = client.get_table(f"{project}.{dataset}.{schema_table}").schema
    names = {column.name for column in schema}
    missing = [name for name in BASE_COLUMNS if name not in names]
    if missing:
        raise NoExportTables(f"{schema_table} is missing GA4 export columns: {', '.join(missing)}.")
    return BASE_COLUMNS + [name for name in OPTIONAL_COLUMNS if name in names], len(in_range)


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
    scope: str = READONLY_SCOPE,
    client=None,
    on_estimate: Callable[[int, int], None] | None = None,
) -> ImportResult:
    """Import one date range of a GA4 export as Rabbit touchpoints.

    Function entry point for the CLI and a future MCP server. Dry-runs first
    and raises :class:`ByteLimitExceeded` before running anything billable
    when the estimate is above ``max_bytes``. ``on_estimate(bytes, tables)``
    is called with the dry-run estimate and the number of daily tables read.
    Google API errors are raised as :class:`ImportErrorBase` subclasses.
    """
    from google.api_core.exceptions import GoogleAPIError
    from google.auth.exceptions import GoogleAuthError

    validate_arguments(project, dataset, start, end, conversion_event)
    if max_bytes <= 0:
        raise InvalidArgument("--max-bytes must be positive.")
    try:
        client = client or make_client(billing_project or project, scope)
        columns, table_count = _available_columns(client, project, dataset, start, end)
        sql = build_query(project, dataset, columns)

        try:
            dry = client.query(
                sql,
                job_config=_job_config(start, end, conversion_event, dry_run=True, max_bytes=max_bytes),
                api_method="QUERY",
            )
        except KeyError as exc:
            # The client builds a job from the jobs.query response and expects
            # a jobReference; a dry-run response without one cannot be read.
            raise BigQueryFailed(
                f"The dry-run response had no {exc.args[0] if exc.args else 'job'} field, so "
                "the bytes estimate could not be read and the cost guard cannot run. "
                "Nothing was queried."
            ) from exc
        if dry.total_bytes_processed is None:
            raise BigQueryFailed(
                "The dry run returned no bytes estimate, so the cost guard cannot run. "
                "Nothing was queried."
            )
        estimated = int(dry.total_bytes_processed)
        if on_estimate:
            on_estimate(estimated, table_count)
        if estimated > max_bytes:
            raise ByteLimitExceeded(estimated, max_bytes)

        job = client.query(
            sql,
            job_config=_job_config(start, end, conversion_event, dry_run=False, max_bytes=max_bytes),
            api_method="QUERY",
        )
        rows = list(job.result())
    except GoogleAPIError as exc:
        raise _translate(exc) from exc
    except GoogleAuthError as exc:
        # e.g. RefreshError: expired or revoked ADC. The message names no secret.
        raise AccessDenied(
            "Google credentials could not be used ("
            f"{type(exc).__name__}). Re-run `gcloud auth application-default login`."
        ) from exc
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
            "estimate against --max-bytes first. Exit codes: 0 ok, 2 bad argument "
            "or no export tables, 3 refused by the dry-run guard, 4 BigQuery refused "
            "over maximum_bytes_billed, 5 credentials or permission, 6 other BigQuery error."
        ),
    )
    parser.add_argument("--project", required=True, help="GCP project that holds the export")
    parser.add_argument("--dataset", required=True, help="GA4 export dataset, e.g. analytics_123456789")
    parser.add_argument("--start", required=True, help="first export day, YYYYMMDD (property time zone)")
    parser.add_argument("--end", required=True, help="last export day, YYYYMMDD (property time zone)")
    parser.add_argument("--conversion-event", required=True, help="GA4 event name, e.g. purchase")
    parser.add_argument("--out", help="write touchpoints CSV here (default: stdout)")
    parser.add_argument(
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"refuse to run above this many bytes; sets maximum_bytes_billed (default {DEFAULT_MAX_BYTES}, 10 GiB)",
    )
    parser.add_argument("--billing-project", help="project billed for the query (default: --project)")
    parser.add_argument(
        "--oauth-scope",
        choices=sorted(SCOPE_CHOICES),
        default="cloud-platform.read-only",
        help="read-only OAuth scope requested from ADC (default cloud-platform.read-only)",
    )
    return parser


def main(argv: list[str] | None = None, *, client=None) -> int:
    args = _parser().parse_args(argv)
    err = sys.stderr

    def report_estimate(estimated: int, tables: int):
        floor = tables * MIN_BILLED_BYTES_PER_TABLE
        print(
            f"Dry run: this query will process {format_bytes(estimated)} ({estimated} bytes) "
            f"from {tables} daily tables; limit --max-bytes {format_bytes(args.max_bytes)}. "
            f"On-demand billing charges at least 10 MB per table ({format_bytes(floor)} here).",
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
            scope=SCOPE_CHOICES[args.oauth_scope],
            client=client,
            on_estimate=report_estimate,
        )
    except ByteLimitExceeded as exc:
        print(f"Refused: {exc}", file=err)
        return exc.exit_code
    except ImportErrorBase as exc:
        print(f"Error: {exc}", file=err)
        return exc.exit_code

    frame, stats = result.frame, result.stats
    print(
        f"Read {result.source_rows} export rows: {stats['session_starts']} session_start "
        f"touchpoints and {stats['conversions']} '{args.conversion_event}' conversions "
        f"for {frame['customer_id'].nunique()} customers; "
        f"{stats['skipped_no_identity']} rows skipped with no user id "
        "(e.g. consent-denied traffic).",
        file=err,
    )
    print(
        "Channel source: "
        f"{stats['channel_from_collected_utm']} UTM tags, "
        f"{stats['channel_from_collected_gclid']} gclid (google / cpc), "
        f"{stats['channel_from_last_non_direct_click']} GA4 last non-direct click, "
        f"{stats['channel_from_event_params']} event params (exported before July 2024), "
        f"{stats['channel_direct']} direct.",
        file=err,
    )
    print(
        "Untagged sessions take GA4's last non-direct session source, as in GA4's "
        "session source/medium, so direct is undercounted and a returning visitor's "
        "earlier source can repeat as a touch.",
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
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
