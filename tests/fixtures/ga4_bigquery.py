"""Offline stand-in for google.cloud.bigquery.Client over GA4 fixture rows.

The rows in tests/fixtures/ga4/events_rows.json are hand-built in the GA4
BigQuery export shape (column names and nesting from the export schema) with
made-up IDs. No real GA4 property or Google API is involved.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parent / "ga4"
EVENTS_ROWS = FIXTURE_DIR / "events_rows.json"
EQUIVALENT_CSV = FIXTURE_DIR / "equivalent_touchpoints.csv"

# Top-level columns of a current GA4 export daily table (subset is enough).
EXPORT_COLUMNS = [
    "event_date", "event_timestamp", "event_name", "event_params", "user_id",
    "user_pseudo_id", "device", "geo", "traffic_source", "ecommerce", "items",
    "collected_traffic_source", "session_traffic_source_last_click",
]


def load_rows():
    return json.loads(EVENTS_ROWS.read_text())


@dataclass
class _Table:
    table_id: str
    schema: list = field(default_factory=list)


@dataclass
class _Column:
    name: str


class FakeJob:
    def __init__(self, rows, total_bytes_processed, dry_run):
        self._rows = rows
        self.total_bytes_processed = total_bytes_processed
        self.dry_run = dry_run

    def result(self):
        if self.dry_run:
            raise AssertionError("result() called on a dry-run job")
        return iter(self._rows)


class FakeBigQueryClient:
    """Records every call; returns fixture rows for the non-dry-run query."""

    def __init__(self, rows=None, estimated_bytes=52_428_800, columns=None,
                 days=("20240301", "20240302", "20240303")):
        self.rows = load_rows() if rows is None else rows
        self.estimated_bytes = estimated_bytes
        self.columns = columns or EXPORT_COLUMNS
        self.days = days
        self.queries = []

    def list_tables(self, dataset_ref):
        tables = [_Table(f"events_{day}") for day in self.days]
        return tables + [_Table(f"events_intraday_{self.days[-1]}"), _Table("pseudonymous_users_20240301")]

    def get_table(self, table_ref):
        return _Table(table_ref.rsplit(".", 1)[-1], [_Column(name) for name in self.columns])

    def query(self, sql, job_config=None, api_method="INSERT", **kwargs):
        self.queries.append({"sql": sql, "job_config": job_config, "api_method": api_method})
        if job_config is not None and job_config.dry_run:
            return FakeJob([], self.estimated_bytes, True)
        return FakeJob(self.rows, self.estimated_bytes, False)
