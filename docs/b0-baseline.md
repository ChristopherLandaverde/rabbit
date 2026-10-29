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

The known-failure list contains one exact pytest node ID for each of the 66
currently failing tests and four `module:` entries for the modules that fail
during collection. Each entry is grouped under a reason from this baseline.
`conftest.py` marks matching tests `xfail(strict=True)` and reads collection
modules into `collect_ignore`. Strict xfails ensure that a known failure which
starts passing makes CI fail until its line is deleted from the list. New test
failures and regressions in tests not listed there remain regular failures.

The CI and local command is:

```text
python -m pytest -q
300 passed, 22 skipped, 66 xfailed, 155310 warnings in 13.96s
```

After the #27 time-decay fix (two new attribution unit tests, no known failure
changed state):

```text
302 passed, 22 skipped, 66 xfailed, 155310 warnings in 9.01s
```

Baseline collection errors represented in `tests/known_failures.txt`:

| Test group | Count | Reason |
|---|---:|---|
| `tests/integration/test_api_endpoints.py` and `tests/performance/test_benchmarks.py` | 2 errors | Both import `sample_csv_file` from `tests.fixtures.app`, where that fixture does not exist. |
| `tests/integration/test_phase3_integration.py` | 1 error | A synchronous test contains `await`, causing `SyntaxError: 'await' outside async function`. |
| `tests/performance/test_phase3_performance.py` | 1 error | Synchronous test functions (including a nested worker) contain `await`, causing the same syntax error. |

The 66 executed failures, now represented as strict xfails, are grouped by file below.

| Test group | Failed | Observed reason |
|---|---:|---|
| `tests/integration/test_phase4_integration.py` | 8 | Redis is not running at `localhost:6379`; cache integration expectations fail and health reports the Redis-backed dependency as unhealthy. |
| `tests/performance/test_phase4_performance.py` | 12 | Redis-backed cache operations fail without Redis; metrics tests expect 10,000/100,000 records while the collector reports 1,000. |
| `tests/unit/test_api_endpoints_phase3.py` | 21 | Requests in the tests receive HTTP 400 where the tests expect success or specific 413/422/500 responses; endpoint validation behavior and fixtures do not match those expectations. |
| `tests/unit/test_logging.py` | 9 | Logger setup and emitted logging behavior do not match the handlers, authentication event, request-error, and masking behavior asserted by these tests. |
| `tests/unit/test_monitoring.py` | 1 | The monitoring integration expects a healthy backing dependency, but Redis is unavailable and health is unhealthy. |
| `tests/unit/test_secure_api.py` | 14 | Secure API tests include cache expectations that miss without Redis, file-parsing error paths that raise `NameError: json is not defined`, and response expectations that do not match current route behavior. |
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

