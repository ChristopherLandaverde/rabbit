# Rabbit B0 baseline

## Environment and dependency install

Verified with Python 3.12.15 on Linux. From a newly created repo-local `.venv`:

```text
$ python --version
Python 3.12.15
$ python -m pip install -r requirements.txt
Successfully installed ... fastapi-0.104.1 ... numpy-1.26.2 ... pandas-2.1.4 ... pyarrow-14.0.1 ... scikit-learn-1.5.0 ...
```

The pinned runtime packages installed successfully on Python 3.12, so no major dependency upgrade was needed. The full pytest run shows independent pre-existing test failures; no tests have been marked xfail.

## Test suite state

Command used to execute collected tests despite collection errors:

```text
python -m pytest -q --continue-on-collection-errors --disable-warnings
66 failed, 300 passed, 22 skipped, 155311 warnings, 4 errors in 14.26s
```

The regular `python -m pytest -q` also exits unsuccessfully at collection. The four collection errors are:

| Test group | Count | Reason |
|---|---:|---|
| `tests/integration/test_api_endpoints.py` and `tests/performance/test_benchmarks.py` | 2 errors | Both import `sample_csv_file` from `tests.fixtures.app`, where that fixture does not exist. |
| `tests/integration/test_phase3_integration.py` | 1 error | A synchronous test contains `await`, causing `SyntaxError: 'await' outside async function`. |
| `tests/performance/test_phase3_performance.py` | 1 error | Synchronous test functions (including a nested worker) contain `await`, causing the same syntax error. |

The 67 executed failures are grouped by file below. These failures remain visible in CI; none were xfailed because the individual test outcomes were not established before the baseline run.

| Test group | Failed | Observed reason |
|---|---:|---|
| `tests/integration/test_phase4_integration.py` | 8 | Redis is not running at `localhost:6379`; cache integration expectations fail and health reports the Redis-backed dependency as unhealthy. |
| `tests/performance/test_phase4_performance.py` | 12 | Redis-backed cache operations fail without Redis; metrics tests expect 10,000/100,000 records while the collector reports 1,000. |
| `tests/unit/test_api_endpoints_phase3.py` | 21 | Requests in the tests receive HTTP 400 where the tests expect success or specific 413/422/500 responses; endpoint validation behavior and fixtures do not match those expectations. |
| `tests/unit/test_logging.py` | 9 | Logger setup and emitted logging behavior do not match the handlers, authentication event, request-error, and masking behavior asserted by these tests. |
| `tests/unit/test_monitoring.py` | 1 | The monitoring integration expects a healthy backing dependency, but Redis is unavailable and health is unhealthy. |
| `tests/unit/test_secure_api.py` | 14 | Secure API tests include cache expectations that miss without Redis, file-parsing error paths that raise `NameError: json is not defined`, and response expectations that do not match current route behavior. |
| `tests/unit/test_security.py` | 1 | The development fallback API key is rejected by the current key-validation behavior. |

This is the current observed test state, not a claim that all failure causes were introduced by B0. The logging import boot issue was fixed so the fresh-checkout API and remaining tests can load; the test contract failures above are not hidden or changed here.

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

No attribution calculations or model code were changed.
