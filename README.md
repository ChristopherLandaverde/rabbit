<p align="center">
  <img src="docs/media/logo.png" width="96" height="96" alt="Rabbit logo: a paper-coloured rabbit head on a dark green tile, its two ears forking from one point like two attribution paths">
</p>

<h1 align="center">Rabbit</h1>

<p align="center">
  <strong>The attribution model you pick moves your budget. See by how much before you commit to one.</strong>
</p>

<p align="center">
  5 rule-based attribution models · self-hosted API · CSV of touchpoints in, each channel's credit share out
</p>

<p align="center">
  <a href="https://github.com/ChristopherLandaverde/rabbit/actions/workflows/ci.yml"><img src="https://github.com/ChristopherLandaverde/rabbit/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/ChristopherLandaverde/rabbit?color=10231F" alt="License: MIT"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> · <a href="#same-data-five-models">Same data, five models</a> · <a href="#known-limits">Known limits</a> · <a href="#status">Status</a> · <a href="docs/usage.md">Usage guide</a>
</p>

On the bundled sample of 10 touchpoints, email gets **33%** of conversion credit under first-touch and **67%** under last-touch. Same data, same conversions; only the model changed.

Rabbit is a small self-hosted API for marketing analysts and RevOps people choosing or defending an attribution model, and for engineers who want an attribution endpoint they run themselves. Post a CSV of touchpoints; get each channel's share of conversion credit under first-touch, last-touch, linear, time-decay or position-based. Results describe attribution under the named model; they do not estimate causal impact.

**Status: in active development again.** The v1 API is the supported path; an experimental v2 API, now up to milestone M3b (several models in one analysis, with a side-by-side comparison), runs behind a flag. See [Status](#status).

## Same data, five models

<p align="center">
  <img src="docs/media/five-models.gif" width="880" alt="Terminal frames of real Rabbit API output on the bundled test_data.csv: the same curl request run with model_type first_touch, last_touch, linear and position_based. Email's credit share goes 33%, 67%, 39%, 47%; paid_search is absent under first_touch and last_touch, then gets 19% under linear and 10% under position_based.">
  <br><sub>Real API responses on the bundled <code>test_data.csv</code>, one model per frame, from the quick-start request below. Channels with no credit are left out; <code>time_decay</code> is skipped because it matches <code>linear</code> on this sample.</sub>
</p>

Share of conversion credit per channel on `test_data.csv` (3 customers, 10 touchpoints, 3 conversions), real API output rounded to whole percent:

| Channel | `first_touch` | `last_touch` | `linear` | `time_decay` | `position_based` |
|---|---:|---:|---:|---:|---:|
| email | 33% | **67%** | 39% | 39% | 47% |
| organic | 33% | 33% | 22% | 22% | 27% |
| social | 33% | 0% | 19% | 19% | 17% |
| paid_search | 0% | 0% | 19% | 19% | 10% |

Paid search touched 2 of the 3 journeys and gets nothing under either single-touch model. Social drops from a third of the credit to zero between first-touch and last-touch. If you set budgets from one model without looking at the others, that swing goes in unexamined. (`time_decay` matches `linear` here because the sample's journeys last 3 hours or less against a 7-day default half-life; see the [usage guide](docs/usage.md#attribution-models).)

## What you get

- **The spread across models, on your own data.** Run one CSV through all five rule-based models and see which channels' credit depends on the model choice.
- **Credit and revenue per channel.** Each response gives every channel's share of credit, the revenue that share represents, and a confidence score.
- **Assumptions you can change.** Set the time-decay half-life and the position-based first/last weights per request.
- **Journeys built from raw touchpoints.** Rabbit links rows by `customer_id`, falling back to session + email or email alone.
- **Runs on your machine.** You start the server; your CSV goes to it, and the v1 code makes no outbound network calls.

## Who it's for

- **Marketing analysts** deciding which attribution model to report on, who want to see what each one does to channel credit first.
- **RevOps leads** defending a model choice, who need to show what the alternatives would have said.
- **Engineers** who need a small attribution API to run locally or behind their own tooling.

## Quick start

Requires Python 3.12, [`uv`](https://docs.astral.sh/uv/) ([pip alternative](docs/usage.md#install-with-pip-instead-of-uv)) and `jq` for the last step.

```bash
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
python run.py
```

The API listens on `http://localhost:8000`. In a second terminal, from the repo root, run the bundled sample through all five models:

```bash
for model in first_touch last_touch linear time_decay position_based; do
  printf '%-15s' "$model"
  curl -s -X POST http://127.0.0.1:8000/attribution/analyze \
    -F 'file=@test_data.csv' -F "model_type=$model" \
    | jq -c '.results.channel_attributions | map_values(.credit * 100 | round)'
done
```

You should see the table above, as percent of credit per channel (channels with no credit are left out):

```text
first_touch    {"email":33,"organic":33,"social":33}
last_touch     {"email":67,"organic":33}
linear         {"email":39,"paid_search":19,"social":19,"organic":22}
time_decay     {"email":39,"paid_search":19,"social":19,"organic":22}
position_based {"email":47,"paid_search":10,"social":17,"organic":27}
```

Then swap in your own file. The [usage guide](docs/usage.md) covers the input columns, model parameters and the full response; interactive API docs are at <http://localhost:8000/docs>.

## Live import from GA4 BigQuery

If your GA4 property exports to BigQuery, Rabbit can read the export directly instead of you building a CSV. The importer reads `<project>.<dataset>.events_*` read-only for a date range and writes the same touchpoint CSV the API takes, so all five models run on it unchanged.

**Fixture-verified; not yet run against a real GA4 export.** It is tested against hand-built rows in GA4 export shape, with made-up IDs, through a mocked BigQuery client. The sample output below comes from those fixtures, not from a live property.

```bash
python -m src.importers.ga4_bigquery --project my-gcp-project --dataset analytics_123456789 \
  --start 20240301 --end 20240315 --conversion-event purchase --out ga4_touchpoints.csv
```

- **Credentials** come from Application Default Credentials on the machine that runs the importer (`gcloud auth application-default login`, or `GOOGLE_APPLICATION_CREDENTIALS`). Rabbit never takes Google credentials in an HTTP request, and never stores or logs them. There is no API endpoint for this yet; it runs as a local CLI or Python function (`import_ga4`).
- **Scope:** `https://www.googleapis.com/auth/cloud-platform.read-only` by default. Google's BigQuery API discovery document (revision 20260811) doesn't list the narrower `bigquery.readonly` for running queries, though third-party reports say it works; `--oauth-scope bigquery.readonly` requests it so a first live run can check. The importer sends one `SELECT` through `jobs.query` and never writes.
- **Roles:** BigQuery Data Viewer on the export dataset and BigQuery Job User on the project that pays for the query.
- **Cost:** the query is billed to your GCP project (`--billing-project`, default `--project`) at BigQuery's on-demand rate, with a minimum of 10 MB per daily table read. `--start` and `--end` are required, and the query reads only the columns it needs from those days' tables. Every run does a free dry run first and prints the bytes it will process. Above `--max-bytes` (default 10 GiB) it stops before running anything billable (exit 3); the real query also sets BigQuery's `maximum_bytes_billed` to the same limit (exit 4 if BigQuery refuses it).
- **Channel** is GA4's own session source/medium: UTM tags, then a `gclid` as `google / cpc`, then GA4's last non-direct click. Untagged sessions therefore take the visitor's last non-direct source, as they do in GA4's reports, so `direct` is undercounted and an earlier source can repeat as a touch.

Output from `python scripts/ga4_fixture_demo.py`, which runs the same CLI on the fixture rows (the 50 MiB estimate is the stand-in client's fixed number):

```text
Dry run: this query will process 50.00 MiB (52428800 bytes) from 5 daily tables; limit --max-bytes 10.00 GiB. On-demand billing charges at least 10 MB per table (50.00 MiB here).
Read 16 export rows: 12 session_start touchpoints and 4 'purchase' conversions for 6 customers; 0 rows skipped with no user id (e.g. consent-denied traffic).
Channel source: 4 UTM tags, 2 gclid (google / cpc), 7 GA4 last non-direct click, 1 event params (pre-2024 export), 2 direct.
Untagged sessions take GA4's last non-direct session source, as in GA4's session source/medium, so direct is undercounted and a returning visitor's earlier source can repeat as a touch.
Wrote 16 touchpoints to ga4_touchpoints.csv.
Run any model on this file; its credits describe association under the named model, not causal impact.
```

That file through the quick-start loop (`-F 'file=@ga4_touchpoints.csv'`), percent of credit per channel under each model:

```text
first_touch    {"google / cpc":25,"google / organic":25,"newsletter / email":25,"direct":25}
last_touch     {"newsletter / email":50,"google / organic":25,"google / cpc":25}
linear         {"google / cpc":21,"newsletter / email":42,"google / organic":25,"direct":6,"facebook / social":6}
time_decay     {"google / cpc":26,"newsletter / email":38,"google / organic":25,"direct":5,"facebook / social":6}
position_based {"google / cpc":23,"newsletter / email":40,"google / organic":25,"direct":10,"facebook / social":2}
```

The field mapping, exit codes and limits (time zones, journeys cut at `--start`, the last ~72 hours still changing, consent-denied traffic) are in [docs/importers/ga4-bigquery.md](docs/importers/ga4-bigquery.md).

## Known limits

- **Credit is association, not causation.** The `insights` block in each response (for example "Increase budget allocation to email by 20-30%") is generated by fixed rules from the credit shares and sample size. Treat it as a prompt for investigation, not a recommendation backed by an experiment.
- **One model per v1 request.** On the supported v1 API, comparing models means one request per model, as in the quick start. The experimental v2 API can run up to five models in one analysis and return a comparison block (see [Status](#status)).
- **Rule-based models only.** No data-driven (Markov, Shapley) model, no cross-device stitching beyond the identifier columns in the CSV (or GA4 `user_id`, for the importer), no ad-platform connectors.
- **The GA4 importer is fixture-verified only.** It reads `session_start` and one conversion event, follows GA4's last non-direct session source for untagged sessions, skips consent-denied traffic, and has not been run against a real export. See [its limits](docs/importers/ga4-bigquery.md#known-limits).
- **Redis is optional but reported.** Without Redis on `localhost:6379`, analysis still works but `/health` returns HTTP 200 with `"status": "unhealthy"`.
- **Not deployed or published.** There is no hosted instance and no package; run it locally.
- **Frontend and Docker are not the supported path.** The React app in `frontend/` builds in CI, and Docker Compose files exist, but neither was verified for this README.
- **Known test failures are tracked, not hidden.** The v1 suite has pre-existing failures marked as strict xfails in [`tests/known_failures.txt`](tests/known_failures.txt), with reasons in [docs/b0-baseline.md](docs/b0-baseline.md).

## Status

Restarted on 2026-10-30 after a pause at milestone M3a. The v1 API above is the supported path. A v2 API runs behind `RABBIT_V2_ENABLED=true` and needs Postgres and Redis. It has API keys, dataset upload and async analyses (M0–M3a), and with M3b one analysis can run one to five models. With two or more, the response adds a comparison block: each channel's credit under each model, the spread between models, and a `model_agreement_score` (1 minus the mean pairwise Jensen-Shannon divergence, so 1.0 means the models split credit identically). That score describes how much the models agree with each other, not which one is right; see [SPEC_v2 §7](docs/api/SPEC_v2.md#7-comparison-math-model_agreement_score). Planned and not built: idempotency keys, cancel, webhooks, an SDK and a deployment ([roadmap](docs/business/ROADMAP.md), [plan](docs/business/PLAN_v2.md)).

## Development

```bash
source .venv/bin/activate
python -m pytest -q --ignore=tests/v2
```

CI runs this v1 suite and the v2 suite on pushes to `main` and on pull requests; see [docs/usage.md](docs/usage.md#development) for both commands, current results and the frontend build. Contributor and agent conventions are in [AGENTS.md](AGENTS.md).

## License

[MIT](LICENSE)
