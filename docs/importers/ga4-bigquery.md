# GA4 BigQuery importer

`src/importers/ga4_bigquery.py` reads the standard GA4 BigQuery export (`<project>.<dataset>.events_*`) read-only and writes Rabbit's touchpoint CSV. The CSV goes through the existing upload path (`POST /attribution/analyze`, or `POST /v2/datasets` then an analysis) and all five models unchanged. Credits on the result describe association under the named model, not causal impact.

Status: fixture-verified. The mapping, cost guard, error handling and model equivalence are tested against hand-built rows in GA4 export shape with made-up IDs (`tests/fixtures/ga4/events_rows.json`), returned as real `google.cloud.bigquery` `Row` objects by a mocked client. It has not yet been run against a real GA4 export.

## Entry points

- CLI: `python -m src.importers.ga4_bigquery --project P --dataset D --start YYYYMMDD --end YYYYMMDD --conversion-event purchase [--out touchpoints.csv] [--max-bytes N] [--billing-project B] [--oauth-scope cloud-platform.read-only|bigquery.readonly]`. Progress and the dry-run estimate go to stderr; the CSV goes to `--out` or stdout.
- Function: `import_ga4(project, dataset, start, end, conversion_event, *, max_bytes, billing_project=None, scope=..., client=None, on_estimate=None) -> ImportResult` with `.frame` (a pandas DataFrame in the CSV columns), `.estimated_bytes`, `.processed_bytes`, `.source_rows` and `.stats`. This is what a future MCP server calls. Errors are raised as `ImportErrorBase` subclasses carrying the exit code below. `rows_to_touchpoints(rows, conversion_event)` is the pure mapping.
- No v2 endpoint yet. `POST /v2/datasets` takes a file under the caller's API key; a BigQuery read there would run on the server host's own Google credentials, not the caller's, so it is left for the MCP slice, where the importer runs on the user's machine with the user's credentials. Rabbit never accepts Google credentials in an HTTP request.

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. |
| 2 | Bad argument, or no `events_YYYYMMDD` tables in range (also a BigQuery `NotFound`). |
| 3 | Refused by the dry-run guard: the estimate is above `--max-bytes`. Nothing billable ran. |
| 4 | BigQuery refused the real query because it would bill more than `maximum_bytes_billed` (`--max-bytes`). |
| 5 | No Application Default Credentials, credentials that can't be used (for example an expired or revoked token, `RefreshError`), or BigQuery denied access (missing role or scope). |
| 6 | Any other BigQuery error, including a dry run that returned no bytes estimate or a dry-run response the client could not read (no `jobReference`). |

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

- `_TABLE_SUFFIX BETWEEN` prunes the scan to the daily tables in range. `events_intraday_*` sorts after every date and is never read. GA4 360 `events_fresh_*` tables are a different table prefix and are not considered.
- Only the listed columns are selected. BigQuery bills by columns read, so this costs a fraction of `SELECT *`.
- A wildcard query takes its schema from the most recently created table matching `events_*`. That can be today's `events_intraday_*` table or a day outside the range. The importer reads that table's schema and selects `collected_traffic_source` (added to the export in June 2023), `session_traffic_source_last_click` (July 2024; its `cross_channel_campaign` record followed in October 2024) and `ecommerce` only when it has them. These dates come from third-party write-ups of the export's changes (for example Analytica House, "GA4 BigQuery export evolution: traffic sources"), not from a Google page this change could reach.
- Dates and the conversion event are query parameters. Project and dataset are checked in full against GCP's id rules before they go into the table name. `--conversion-event session_start` is rejected.

## Field mapping

| Rabbit column | From GA4 export | Notes |
|---|---|---|
| `customer_id` | `user:<user_id>`, else `ga4:<user_pseudo_id>` | If any selected row for a `user_pseudo_id` has a `user_id`, every row for that device uses it, so devices that log in join one journey. The prefix keeps ids as text: pseudo ids look like numbers (`1234567890.1709280000`), and a CSV holding only those would otherwise parse as floats and lose every touchpoint. |
| `timestamp` | `event_timestamp` | Microseconds since epoch, written as UTC `YYYY-MM-DD HH:MM:SS.ffffff`. |
| `event_type` | `event_name` | The `--conversion-event` becomes `conversion`; `session_start` becomes `view`. Other events are not read. |
| `channel` | See [Channel](#channel) | Written as `source / medium`, lower-cased (`google / cpc`); `source` alone when medium is missing. |
| `campaign_id` | Campaign name from the same record as the channel | Unset values become empty. |
| `session_id` | `user_pseudo_id` + `.` + event param `ga_session_id` | |
| `conversion_value` | `ecommerce.purchase_revenue_in_usd`, else `ecommerce.purchase_revenue`, else event param `value` (double, int or float) | Conversion rows only. The USD field is preferred so a multi-currency property sums in one currency; the fallbacks are in the event's own currency. Negative or non-numeric values become empty so the conversion still counts. |

### Channel

The channel matches what GA4 itself reports as a session's source/medium. Each `session_start` and conversion row takes the first rule that applies:

1. **UTM tags**: `collected_traffic_source.manual_source` / `manual_medium` / `manual_campaign_name`. In a real export this record holds only UTM values and click ids (`gclid`, `dclid`, `srsltid`).
2. **Google Ads auto-tagging**: a `collected_traffic_source.gclid` with no UTM source becomes `google / cpc`, with the campaign from `session_traffic_source_last_click.google_ads_campaign.campaign_name` when present.
3. **GA4's last non-direct click**: `session_traffic_source_last_click`. Untagged organic, referral and direct sessions get their source here. Read from `cross_channel_campaign` source / medium / campaign (in the export from October 2024); when that has no source, from `manual_campaign`, then from `google_ads_campaign` as `google / cpc`. Rows exported from July to October 2024 have only those two.
4. **Event params** `source` / `medium` / `campaign`, used only when the row has no `session_traffic_source_last_click` at all (exported before July 2024).
5. Otherwise **`direct`**. A source that is null, empty, `(not set)`, `(none)`, `(direct)` or `(not provided)` counts as no source at every step.

What this means for the numbers: untagged sessions take GA4's last-non-direct session source, the same as GA4's session source/medium. A direct visit after an email visit counts as an email touch. `direct` is therefore undercounted compared with a strictly session-scoped source, and a returning visitor's earlier source can repeat as a touch, which gives that source more weight under `linear`, `time_decay` and `position_based`.

## Credentials, scope and cost

- Credentials are Application Default Credentials on the machine that runs the importer: `gcloud auth application-default login`, or `GOOGLE_APPLICATION_CREDENTIALS` pointing at a key file. On a server host, that host's own ADC. The importer never accepts credentials as arguments or in an HTTP request, and never stores or logs them.
- OAuth scope: `https://www.googleapis.com/auth/cloud-platform.read-only` by default. The BigQuery v2 discovery document (revision 20260811) does not list `bigquery.readonly` for `jobs.query`, `jobs.getQueryResults`, `jobs.get`, `tables.get` or `tables.list`; the narrowest scope it lists for all of them is `cloud-platform.read-only`. Third-party reports say `bigquery.readonly` does work for queries in practice. `--oauth-scope bigquery.readonly` requests it instead, and the first live smoke run should try it; if it works, it should become the default. `jobs.insert` requires a read-write scope (`bigquery` or `cloud-platform`), so the importer sends both the dry run and the query through `jobs.query` (`api_method="QUERY"` in the Python client).
- IAM: BigQuery Data Viewer (`roles/bigquery.dataViewer`) on the export dataset, and BigQuery Job User (`roles/bigquery.jobUser`) on the billing project.
- Cost: the query bills the billing project (`--billing-project`, default `--project`) at on-demand rates. On-demand billing charges at least 10 MB per table a query reads, so a 30-day range is billed at least 300 MB however small the tables are. Every run dry-runs first and prints the estimate. If the estimate is above `--max-bytes` (default 10 GiB) it stops before anything billable runs (exit 3). The real query also sets `maximum_bytes_billed` to `--max-bytes`, so BigQuery itself fails the query rather than bill more (exit 4).

## Known limits

- **Time zones.** `--start` and `--end` select daily tables, which GA4 cuts in the property's reporting time zone. Timestamps in the output are UTC. A day's table can hold events from two UTC dates.
- **Journeys are truncated at `--start`.** Touches before the first day in range are not read, so a journey that began earlier is credited only from `--start` onward. Pick a start date earlier than the conversions you care about by at least your lookback window.
- **Recent days can still change.** GA4 can update daily tables for up to about 72 hours after the day ends (late hits). Re-run once the range is older than that.
- **Consent-denied traffic is not counted.** With Consent Mode, denied users send cookieless pings with a null `user_pseudo_id`. Those rows have no identity and are skipped; the CLI prints how many.
- **A range that crosses July 2024 mixes two channel sources.** Days exported before July 2024 have no `session_traffic_source_last_click`, so their channel comes from event params; later days use GA4's last non-direct click. The same visit pattern can get a different channel on either side of that date.
- **GA4 360 fresh tables** (`events_fresh_*`) are not read; only the daily `events_YYYYMMDD` tables are.
- **Last-click inheritance.** Untagged sessions take GA4's last non-direct source (see [Channel](#channel)), so `direct` is undercounted and earlier sources can repeat.
- Only `session_start` and the conversion event become touchpoints. Sessions without a `session_start` event (for example Measurement Protocol hits) are not counted as touches.
- Channel is source/medium, not GA4's default channel grouping.
- One conversion event per run.
- Mixed currencies remain only where `purchase_revenue_in_usd` is missing and a fallback value is used.
- Not yet run against a real GA4 export. The scope, the `jobs.query` dry-run path and the error mapping come from Google's API documents and client library, not from a live call.

## Run it offline on the fixtures

```bash
python scripts/ga4_fixture_demo.py
```

This runs the same CLI with a stand-in client over `tests/fixtures/ga4/events_rows.json`. The dry-run estimate it prints (50 MiB) is the stand-in's fixed number.
