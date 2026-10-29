# Rabbit B0 baseline

## Environment and dependency install

Verified with Python 3.12.15 on Linux. From a newly created repo-local `.venv`:

```text
$ python --version
Python 3.12.15
$ python -m pip install -r requirements.txt
Successfully installed ... fastapi-0.104.1 ... numpy-1.26.2 ... pandas-2.1.4 ... pyarrow-14.0.1 ... scikit-learn-1.5.0 ...
```

The pinned runtime packages installed successfully on Python 3.12, so no major dependency upgrade was needed. The test baseline below is recorded in `tests/known_failures.txt` so CI can pass while continuing to fail on regressions.

## Test suite state

`tests/known_failures.txt` contains exact pytest node IDs for known failures and
four `module:` entries for collection errors. `conftest.py` marks matching
tests `xfail(strict=True)` and reads collection modules into `collect_ignore`.
Strict xfails ensure that a known failure which starts passing makes CI fail
until its line is deleted. New test failures and regressions remain ordinary
failures.

`tests/redis_required.txt` separately lists tests that exercise live Redis.
`conftest.py` probes `REDIS_HOST`, `REDIS_PORT`, and `REDIS_DB` once per session;
those tests skip with `needs Redis` if the endpoint is unreachable and run
normally when it responds. CI points these variables and `DATABASE_URL` at its
Redis 7 and Postgres 16 services. The v2 Redis fixture uses the configured
service instead of starting a second Testcontainers Redis without a readiness
check. That startup race caused intermittent connection resets/timeouts in v2;
locally, v2 uses a reachable service or skips with `needs Redis`.

With Redis and Postgres running, the CI suite commands produced:

```text
python -m pytest -q --ignore=tests/v2
315 passed, 22 skipped, 53 xfailed, 156523 warnings in 12.91s

python -m pytest -q tests/v2
5 passed, 5 warnings in 0.96s
```

After the v2 analyses slice (#16), with Redis 7 and Postgres 16 running:

```text
python -m pytest -q --ignore=tests/v2
315 passed, 22 skipped, 53 xfailed, 156524 warnings in 13.09s

python -m pytest -q tests/v2
48 passed, 48 warnings in 12.55s
```

With Redis unavailable, the v1 command produced:

```text
python -m pytest -q --ignore=tests/v2
302 passed, 36 skipped, 52 xfailed, 155307 warnings in 5.72s
```

Redis-related strict xfails that pass with the service were removed. Any live
Redis tests that still fail for a separate reason remain strict xfails with
that cause recorded; other live Redis checks pass with the service.

Baseline collection errors represented in `tests/known_failures.txt`:

| Test group | Count | Reason |
|---|---:|---|
| `tests/integration/test_api_endpoints.py` and `tests/performance/test_benchmarks.py` | 2 errors | Both import `sample_csv_file` from `tests.fixtures.app`, where that fixture does not exist. |
| `tests/integration/test_phase3_integration.py` | 1 error | A synchronous test contains `await`, causing `SyntaxError: 'await' outside async function`. |
| `tests/performance/test_phase3_performance.py` | 1 error | Synchronous test functions (including a nested worker) contain `await`, causing the same syntax error. |

The remaining strict xfails are grouped by file below.

| Test group | Failed | Observed reason |
|---|---:|---|
| `tests/integration/test_phase4_integration.py` | 2 | One test calls async middleware without awaiting it; another patches the shared `redis.Redis` class, contaminating its CacheManager mock. |
| `tests/performance/test_phase4_performance.py` | 5 | Metrics tests expect 10,000/100,000 records while the collector reports 1,000; two tests omit `import json`; one expects a one-second system probe to finish within 0.5 seconds. |
| `tests/unit/test_api_endpoints_phase3.py` | 21 | Requests in the tests receive HTTP 400 where the tests expect success or specific 413/422/500 responses; endpoint validation behavior and fixtures do not match those expectations. |
| `tests/unit/test_logging.py` | 9 | Logger setup and emitted logging behavior do not match the handlers, authentication event, request-error, and masking behavior asserted by these tests. |
| `tests/unit/test_monitoring.py` | 1 | The monitoring workflow assumes process-global counters start at zero, but earlier tests have recorded requests. |
| `tests/unit/test_secure_api.py` | 14 | Secure API tests retain request/response and cache contract mismatches; file-parsing error paths also raise `NameError: json is not defined`. |
| `tests/unit/test_security.py` | 1 | The development fallback API key is rejected by the current key-validation behavior. |

This is the observed baseline, not a claim that all failure causes were introduced by B0. When a listed test is fixed, delete its node ID from `tests/known_failures.txt`; when a collection-error module is fixed, delete its `module:` entry. The logging import boot issue was fixed so the fresh-checkout API and remaining tests can load; the test contract failures above are not changed here.

## Attribution model outputs

The old attribution code ran under the pinned dependencies on Python 3.12, so these outputs are the pre-change baseline. Input was `test_data.csv`; identity resolution selected `customer_id`, producing 3 journeys, all 3 converting. Outputs below are raw aggregate model credits across those journeys, before `AttributionService` normalizes aggregate credits to sum to 1.

```text
first_touch:   {"email": 1.0, "organic": 1.0, "social": 1.0}
last_touch:    {"email": 2.0, "organic": 1.0}
linear:        {"email": 1.1666666666666665, "organic": 0.6666666666666666,
                "paid_search": 0.5833333333333333, "social": 0.5833333333333333}
time_decay:    {"email": 1.1666666666666665, "organic": 0.6666666666666666,
                "paid_search": 0.5833333333333333, "social": 0.5833333333333333}
position_based: {"email": 1.4000000000000001, "organic": 0.8,
                 "paid_search": 0.29999999999999993, "social": 0.5}
```

No attribution calculations or model code were changed in B0.

### Time decay fix (#27)

In the B0 outputs above, `time_decay` is identical to `linear`. That was a bug,
not a property of the data: `TimeDecayAttributionModel` measured the gap to
conversion with `timedelta.days`, which truncates to whole days. Every journey
in `test_data.csv` spans 2-3 hours, so every gap became 0 days, every weight
became `2 ** 0 = 1`, and the model degenerated to equal credit. Timestamps were
parsed correctly and the 7-day half-life unit was correct.

The fix uses fractional days (`total_seconds() / 86400`). Outputs on
`test_data.csv` after the fix (same command, raw aggregate credits):

```text
first_touch:   {"email": 1.0, "organic": 1.0, "social": 1.0}
last_touch:    {"email": 2.0, "organic": 1.0}
linear:        {"email": 1.1666666666666665, "organic": 0.6666666666666666,
                "paid_search": 0.5833333333333333, "social": 0.5833333333333333}
time_decay:    {"email": 1.1675575570284877, "organic": 0.6664402106746266,
                "paid_search": 0.5836586373343504, "social": 0.5823435949625355}
position_based: {"email": 1.4000000000000001, "organic": 0.8,
                 "paid_search": 0.29999999999999993, "social": 0.5}
```

Only `time_decay` changed. It now differs from `linear`, but only slightly:
with the default 7-day half-life, a touchpoint 3 hours before conversion keeps
`2 ** (-3 / 168) = 98.8%` of the weight of the converting touch. Use a shorter
`half_life_days` to see a larger recency effect on short journeys. The four
other models are byte-for-byte unchanged and remain the regression reference.

