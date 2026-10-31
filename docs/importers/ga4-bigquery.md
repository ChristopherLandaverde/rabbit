# GA4 BigQuery importer

`src/importers/ga4_bigquery.py` reads the standard GA4 BigQuery export (`<project>.<dataset>.events_*`) read-only and writes Rabbit's touchpoint CSV. The CSV goes through the existing upload path (`POST /attribution/analyze`, or `POST /v2/datasets` then an analysis) and all five models unchanged. Credits on the result describe association under the named model, not causal impact.

Status: fixture-verified. The mapping, cost guard and model equivalence are tested against hand-built rows in GA4 export shape with made-up IDs (`tests/fixtures/ga4/events_rows.json`) and a mocked BigQuery client. It has not yet been run against a real GA4 export.

## Entry points

- CLI: `python -m src.importers.ga4_bigquery --project P --dataset D --start YYYYMMDD --end YYYYMMDD --conversion-event purchase [--out touchpoints.csv] [--max-bytes N] [--billing-project B]`. Progress and the dry-run estimate go to stderr; the CSV goes to `--out` or stdout. Exit codes: 0 success, 2 bad argument or no export tables in range, 3 refused by the byte guard.
- Function: `import_ga4(project, dataset, start, end, conversion_event, *, max_bytes, billing_project=None, client=None, on_estimate=None) -> ImportResult` with `.frame` (a pandas DataFrame in the CSV columns), `.estimated_bytes`, `.processed_bytes`, `.source_rows` and `.stats`. This is what a future MCP server calls. `rows_to_touchpoints(rows, conversion_event)` is the pure mapping.
- No v2 endpoint yet. `POST /v2/datasets` takes a file under the caller's API key; a BigQuery read would run on the server's own Google credentials, not the caller's, so it is left for the MCP slice, where the importer runs on the user's machine with the user's credentials.

## Which rows are read

One SELECT, nothing else (no DDL, DML, scripts or temp tables):

```sql
SELECT
  event_timestamp, event_name, user_pseudo_id, user_id, event_params,
  collected_traffic_source, session_traffic_source_last_click, ecommerce
FROM `<project>.<dataset>.events_*`
WHERE _TABLE_SUFFIX BETWEEN @start AND @end
  AND event_name IN ('session_start', @conversion_event)
ORDER BY user_pseudo_id, event_timestamp
```

- `_TABLE_SUFFIX BETWEEN` prunes the scan to the daily tables in range. `events_intraday_*` sorts after every date and is never included.
- Only the listed columns are selected. BigQuery bills by columns read, so this costs a fraction of `SELECT *`.
- `collected_traffic_source` (added to the export in 2023), `session_traffic_source_last_click` (2024) and `ecommerce` are selected only when the newest daily table in range has them; older exports fall back to event parameters.
- Dates and the conversion event are query parameters. Project and dataset are validated against GCP's id rules before they go into the table name.

## Field mapping

| Rabbit column | From GA4 export | Notes |
|---|---|---|
| `customer_id` | `user_id`, else `user_pseudo_id` | If any selected row for a `user_pseudo_id` has a `user_id`, every row for that device uses it, so devices that log in join one journey. |
| `timestamp` | `event_timestamp` | Microseconds since epoch, written as UTC `YYYY-MM-DD HH:MM:SS.ffffff`. |
| `event_type` | `event_name` | The `--conversion-event` becomes `conversion`; `session_start` becomes `view`. Other events are not read. |
| `channel` | source and medium, first match of: 1. `collected_traffic_source.manual_source` / `manual_medium`; 2. `session_traffic_source_last_click.manual_campaign.source` / `medium`; 3. event params `source` / `medium` | Written as `source / medium`, lower-cased (`google / cpc`); `source` alone when medium is missing. A source that is null, empty, `(not set)`, `(none)`, `(direct)` or `(not provided)` moves on to the next field; when none has a source the channel is `direct`. |
| `campaign_id` | campaign name from the same field as the channel (`manual_campaign_name`, `campaign_name` or the `campaign` param) | Unset values become empty. |
| `session_id` | `user_pseudo_id` + `.` + event param `ga_session_id` | |
| `conversion_value` | `ecommerce.purchase_revenue`, else event param `value` (double, int or float) | Conversion rows only. Negative or non-numeric values become empty so the conversion is still counted. |

Why this order for channel: `collected_traffic_source` is what was collected on that event, so it describes that touch. `session_traffic_source_last_click` applies GA4's last non-direct click rule, which can credit an earlier session's source to a direct session; it is used only when nothing was collected. Event params are the source in exports from before 2023.

## Credentials, scope and cost

- Credentials are Application Default Credentials on the machine that runs the importer (`gcloud auth application-default login`, or `GOOGLE_APPLICATION_CREDENTIALS` pointing at a key file). The importer never accepts credentials as arguments or in an HTTP request, and never stores or logs them.
- OAuth scope: `https://www.googleapis.com/auth/cloud-platform.read-only`. The brief asked for `bigquery.readonly`, but the BigQuery v2 API discovery document (revision 20240919) does not list `bigquery.readonly` for `jobs.query`, `jobs.getQueryResults`, `jobs.get`, `tables.get` or `tables.list`. The narrowest scope it lists for all of them is `cloud-platform.read-only`. `jobs.insert` requires a read-write scope (`bigquery` or `cloud-platform`), so the importer sends both the dry run and the query through `jobs.query` (`api_method="QUERY"` in the Python client).
- IAM: BigQuery Data Viewer (`roles/bigquery.dataViewer`) on the export dataset, and BigQuery Job User (`roles/bigquery.jobUser`) on the billing project.
- Cost: the query bills the billing project (`--billing-project`, default `--project`) at on-demand rates. Every run dry-runs first and prints the estimate. If the estimate is above `--max-bytes` (default 10 GiB) it stops before anything billable runs (exit 3). The real query also sets `maximum_bytes_billed` to `--max-bytes`, so BigQuery itself fails the query rather than bill more.

## Known limits

- Only `session_start` and the conversion event become touchpoints. Sessions without a `session_start` event (for example Measurement Protocol hits) are not counted as touches.
- Channel is source/medium, not GA4's default channel grouping.
- `gclid`-only traffic with no UTM source and no `session_traffic_source_last_click` maps to `direct`.
- One conversion event per run.
- Not yet run against a real GA4 export; the scope and `jobs.query` path are from Google's API documents, not from a live call.

## Run it offline on the fixtures

```bash
python scripts/ga4_fixture_demo.py
```

This runs the same CLI with a stand-in client over `tests/fixtures/ga4/events_rows.json`; the dry-run estimate it prints (50 MiB) is the stand-in's fixed number.
