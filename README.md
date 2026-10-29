# Rabbit

**Upload a touchpoint CSV and see how five attribution models split conversion credit across your channels.**

[![CI](https://github.com/ChristopherLandaverde/rabbit/actions/workflows/ci.yml/badge.svg)](https://github.com/ChristopherLandaverde/rabbit/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Quick start](#quick-start) · [Models](#attribution-models) · [Input format](#input-format) · [Known limits](#status-and-known-limits) · [API docs](docs/api/specification.md)

Rabbit is a self-hosted FastAPI service for marketing analysts and RevOps people who want to compare attribution models on their own touchpoint data. You post a CSV of touchpoints (timestamp, channel, event type, customer ID); Rabbit groups them into customer journeys and returns each channel's share of credit under the model you pick. Results describe attribution under the selected model; they do not estimate causal impact.

The same bundled sample file (`test_data.csv`: 3 customers, 10 touchpoints, 3 conversions) under each model, real API output rounded to 3 decimals:

```text
first_touch    {"email":0.333,"organic":0.333,"social":0.333}
last_touch     {"email":0.667,"organic":0.333}
linear         {"email":0.389,"paid_search":0.194,"social":0.194,"organic":0.222}
time_decay     {"email":0.389,"paid_search":0.195,"social":0.194,"organic":0.222}
position_based {"email":0.467,"paid_search":0.1,"social":0.167,"organic":0.267}
```

## Quick start

Requires Python 3.12 and [`uv`](https://docs.astral.sh/uv/) (or see the [pip alternative](#install-with-pip)). `jq` is optional, for trimming the response.

```bash
git clone https://github.com/ChristopherLandaverde/rabbit.git
cd rabbit
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
python run.py
```

The API listens on `http://localhost:8000`. In a second terminal, from the repo root, run the bundled sample through the linear model:

```bash
curl -s -X POST http://127.0.0.1:8000/attribution/analyze \
  -F 'file=@test_data.csv' \
  -F 'model_type=linear' \
  | jq '.results.channel_attributions | map_values(.credit)'
```

You should see each channel's share of credit (sums to 1):

```json
{
  "email": 0.3888888888888889,
  "paid_search": 0.19444444444444445,
  "social": 0.19444444444444445,
  "organic": 0.22222222222222224
}
```

Drop the `jq` pipe to see the full response: per-channel `credit`, `revenue` (total revenue of $225 split by credit, so email gets $87.50) and `confidence`, plus `metadata` (linking method, time range) and `insights`. Interactive API docs are at <http://localhost:8000/docs>.

<details>
<summary id="install-with-pip">Install with pip instead of uv</summary>

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```
</details>

## Attribution models

Pass one of these as `model_type`. Credit is computed per customer journey (each journey's credits sum to 1), summed across journeys, then normalized so the response sums to 1.

| `model_type` | How credit is assigned | Optional parameters |
|---|---|---|
| `first_touch` | 100% to the first touchpoint in the journey | none |
| `last_touch` | 100% to the last touchpoint (usually the conversion event) | none |
| `linear` | Equal share to every touchpoint | none |
| `time_decay` | Weight `2^(-days before conversion / half_life_days)`, so touches closer to the conversion get more | `half_life_days` (default 7) |
| `position_based` | 40% first, 40% last, remaining 20% split across the middle (a two-touch journey splits 50/50) | `first_touch_weight`, `last_touch_weight` (default 0.4 each) |

**Why `time_decay` looks like `linear` on the sample:** every journey in `test_data.csv` lasts 3 hours or less, and with the default 7-day half-life a touch 3 hours before conversion keeps 98.8% of the converting touch's weight. Set a half-life on the scale of your journeys to see recency matter. With `-F 'half_life_days=0.125'` (3 hours) the same file gives:

```text
time_decay     {"email":0.408,"paid_search":0.196,"social":0.175,"organic":0.221}
```

(Before the fix for [#27](https://github.com/ChristopherLandaverde/rabbit/issues/27), time decay rounded each gap down to whole days, so same-day journeys got exactly linear credit. See [docs/b0-baseline.md](docs/b0-baseline.md).)

## Input format

CSV with a header row. Required columns: `timestamp`, `channel`, `event_type`. Optional: `customer_id`, `session_id`, `email`, `campaign_id`, `conversion_value`. Rabbit links touchpoints into journeys using the best available identifier (here, `customer_id`).

```csv
timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,
2024-01-01 11:30:00,paid_search,click,cust_001,
2024-01-01 13:00:00,email,conversion,cust_001,100.00
```

`test_data.csv` in the repo root is a complete example.

## Status and known limits

Rabbit v1 boots on Python 3.12 and its test results are known; a v2 API is planned ([roadmap](docs/business/ROADMAP.md), [plan](docs/business/PLAN_v2.md)).

- **Tests:** `python -m pytest -q` gives 302 passed, 22 skipped, 66 xfailed. The 66 are pre-existing failures tracked as strict xfails in [`tests/known_failures.txt`](tests/known_failures.txt), with reasons in [docs/b0-baseline.md](docs/b0-baseline.md); most need Redis or reflect stale test expectations.
- **Redis is optional but reported:** without Redis on `localhost:6379`, analysis still works but `/health` returns HTTP 200 with `"status": "unhealthy"`.
- **Credit is association, not causation.** The `insights` block (for example "Increase budget allocation to email by 20-30%") is generated by fixed rules from the credit shares and sample size; treat it as a prompt for investigation, not a recommendation backed by an experiment.
- **Rule-based models only.** No data-driven (Markov, Shapley) model, no cross-device stitching beyond the identifier columns in the CSV, no ad-platform connectors.
- **Not deployed or published.** There is no hosted instance or package; run it locally.
- **Frontend and Docker are not the supported path.** The React app in `frontend/` and the Docker Compose files exist but were not verified for this README.

## Development

```bash
source .venv/bin/activate
python -m pytest -q
```

CI runs the same command on pushes to `main` and on pull requests. A test listed in `tests/known_failures.txt` that starts passing fails CI until its line is removed. Agent and contributor conventions are in [AGENTS.md](AGENTS.md).

The React frontend lives in `frontend/` (`npm install && npm run dev`; unverified, see above).

## License

[MIT](LICENSE)
