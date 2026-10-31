# Using the Rabbit v1 API

Details moved out of the README: the models and their parameters, the input format, the response fields and the development commands. For the endpoint-level spec see [api/specification.md](api/specification.md); with the server running, interactive docs are at <http://localhost:8000/docs>.

## Analyze a file

One request runs one model. Post a CSV as `file` and the model as `model_type`:

```bash
curl -s -X POST http://127.0.0.1:8000/attribution/analyze \
  -F 'file=@test_data.csv' \
  -F 'model_type=linear' \
  | jq '.results.channel_attributions | map_values(.credit)'
```

On the bundled `test_data.csv` this returns each channel's share of credit (sums to 1):

```json
{
  "email": 0.3888888888888889,
  "paid_search": 0.19444444444444445,
  "social": 0.19444444444444445,
  "organic": 0.22222222222222224
}
```

Channels that receive no credit under a model are left out of the response.

## Response fields

Drop the `jq` pipe to see the full response:

- `results.total_conversions`, `results.total_revenue` (the sample has 3 conversions and $225).
- `results.channel_attributions.<channel>`: `credit` (share, 0-1), `revenue` (total revenue split by credit, so under `linear` email gets $87.50 of the $225), `conversions` and `confidence`.
- `results.overall_confidence`.
- `metadata`: model used, number of touchpoints analyzed, time range, linking method, processing time.
- `insights`: rule-generated observations and suggestions. They come from fixed rules over the credit shares and sample size, not from an experiment; see Known limits in the [README](../README.md#known-limits).

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

(Before the fix for [#27](https://github.com/ChristopherLandaverde/rabbit/issues/27), time decay rounded each gap down to whole days, so same-day journeys got exactly linear credit. See [b0-baseline.md](b0-baseline.md).)

## Input format

CSV with a header row. Required columns: `timestamp`, `channel`, `event_type`. Optional: `customer_id`, `session_id`, `email`, `campaign_id`, `conversion_value`.

```csv
timestamp,channel,event_type,customer_id,conversion_value
2024-01-01 10:00:00,email,click,cust_001,
2024-01-01 11:30:00,paid_search,click,cust_001,
2024-01-01 13:00:00,email,conversion,cust_001,100.00
```

Rabbit links touchpoints into journeys using the best available identifier: `customer_id` when more than 80% of rows have one, otherwise `session_id` + `email`, otherwise `email` alone, otherwise all rows are treated as one aggregate journey (see `src/core/identity/resolver.py`). `test_data.csv` in the repo root is a complete example (3 customers, 10 touchpoints, 3 conversions, linked by `customer_id`).

Identifier columns (`customer_id`, `session_id`, `campaign_id`, `creative_id`, `email`) are read as text, so numeric-looking ids such as `10423`, `00123` or a GA4 `user_pseudo_id` like `1234567890.1709280000` keep their exact value and every row. Rows that still cannot become a touchpoint (for example a negative `conversion_value`, or no identifier when linking by `customer_id`) are counted: the v1 response reports them in `metadata.rows_dropped`, and a v2 dataset upload lists them as a `rows_dropped` validation warning.

## Install with pip instead of uv

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run.py
```

## Development

CI installs `requirements.txt` and `requirements-test.txt`, then runs two suites:

```bash
source .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest -q --ignore=tests/v2   # v1
python -m pytest -q tests/v2            # v2 (Postgres and Redis; one test needs Docker)
```

Without Redis, the v1 suite gives 302 passed, 36 skipped, 52 xfailed. The xfails are pre-existing failures tracked as strict xfails in [`tests/known_failures.txt`](../tests/known_failures.txt), with reasons in [b0-baseline.md](b0-baseline.md); a listed test that starts passing fails CI until its line is removed. Tests that need live Redis skip with `needs Redis` when it isn't reachable. CI also builds the React frontend in `frontend/` (`npm ci && npm run build`).

Agent and contributor conventions are in [AGENTS.md](../AGENTS.md).
