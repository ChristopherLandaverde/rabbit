"""Offline stand-in for google.cloud.bigquery.Client over GA4 fixture rows.

The rows in tests/fixtures/ga4/events_rows.json are hand-built in the GA4
BigQuery export shape (column names and nesting from the export schema) with
made-up IDs. ``collected_traffic_source`` holds only UTM values and click ids,
as in real exports; untagged sessions carry their source in
``session_traffic_source_last_click``. No real GA4 property or Google API is
involved.

The stand-in returns real ``google.cloud.bigquery.table.Row`` objects holding
only the columns the importer's SELECT names, as the client library would.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from google.cloud.bigquery.table import Row

FIXTURE_DIR = Path(__file__).resolve().parent / "ga4"
EVENTS_ROWS = FIXTURE_DIR / "events_rows.json"
EQUIVALENT_CSV = FIXTURE_DIR / "equivalent_touchpoints.csv"
FIXTURE_DAYS = ("20240301", "20240302", "20240303", "20240308", "20240315")

# Top-level columns of a current GA4 export daily table (subset is enough).
EXPORT_COLUMNS = [
    "event_date", "event_timestamp", "event_name", "event_params", "user_id",
    "user_pseudo_id", "device", "geo", "traffic_source", "ecommerce", "items",
    "collected_traffic_source", "session_traffic_source_last_click",
]


def load_rows():
    return json.loads(EVENTS_ROWS.read_text())


def to_bigquery_rows(rows, columns):
    """Wrap dicts as google.cloud.bigquery Row objects with ``columns`` only."""
    index = {name: position for position, name in enumerate(columns)}
    return [Row(tuple(row.get(name) for name in columns), index) for row in rows]


def selected_columns(sql):
    select = re.search(r"SELECT\s+(.*?)\s+FROM", sql, re.S).group(1)
    return [column.strip() for column in select.split(",")]


@dataclass
class _Table:
    table_id: str
    created: datetime | None = None
    schema: list = field(default_factory=list)


@dataclass
class _Column:
    name: str


class FakeJob:
    def __init__(self, rows, total_bytes_processed, dry_run, error=None):
        self._rows = rows
        self.total_bytes_processed = total_bytes_processed
        self.dry_run = dry_run
        self._error = error

    def result(self):
        if self.dry_run:
            raise AssertionError("result() called on a dry-run job")
        if self._error:
            raise self._error
        return iter(self._rows)


class FakeBigQueryClient:
    """Records every call; returns fixture rows for the non-dry-run query.

    ``columns`` is the schema of the newest table matching ``events_*`` (an
    intraday table, as in a live export). ``query_error`` is raised by the
    real query's ``result()``.
    """

    def __init__(self, rows=None, estimated_bytes=52_428_800, columns=None,
                 days=FIXTURE_DAYS, query_error=None):
        self.rows = load_rows() if rows is None else rows
        self.estimated_bytes = estimated_bytes
        self.columns = columns or EXPORT_COLUMNS
        self.days = days
        self.query_error = query_error
        self.queries = []
        self.schema_reads = []

    def list_tables(self, dataset_ref):
        base = datetime(2024, 3, 1, 9, tzinfo=timezone.utc)
        tables = [_Table(f"events_{day}", base + timedelta(days=i)) for i, day in enumerate(self.days)]
        tables.append(_Table(f"events_intraday_{self.days[-1]}", base + timedelta(days=60)))
        tables.append(_Table("pseudonymous_users_20240301", base + timedelta(days=90)))
        return tables

    def get_table(self, table_ref):
        self.schema_reads.append(table_ref)
        return _Table(table_ref.rsplit(".", 1)[-1], schema=[_Column(name) for name in self.columns])

    def query(self, sql, job_config=None, api_method="INSERT", **kwargs):
        self.queries.append({"sql": sql, "job_config": job_config, "api_method": api_method})
        if job_config is not None and job_config.dry_run:
            return FakeJob([], self.estimated_bytes, True)
        rows = to_bigquery_rows(self.rows, selected_columns(sql))
        return FakeJob(rows, self.estimated_bytes, False, self.query_error)
