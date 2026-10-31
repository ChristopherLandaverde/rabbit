# Rabbit API v2 — Specification

**Status:** Draft for implementation
**Base URL (prod):** `https://api.rabbit.dev/v2` *(placeholder)*
**Base URL (local):** `http://localhost:8000/v2`
**Auth:** Bearer API key (`Authorization: Bearer rk_live_...`)
**Content-Type:** `application/json` unless noted (multipart for uploads)

---

## 1. Conventions

### Authentication
All `/v2/*` endpoints except `/v2/health` require a valid API key.

```
Authorization: Bearer rk_live_<32-byte-base62>
```

Key prefixes:
- `rk_live_` — production. Rate-limited, counted toward future billing, lives on prod data.
- `rk_test_` — test mode. **No rate limit, unlimited touchpoints, isolated from live data.** Every resource created carries `"livemode": false`. Test datasets/analyses cannot be referenced from live keys and vice versa. Intended for CI and SDK examples.

Keys are issued two ways:
- **Self-serve (DX1):** `POST /v2/keys/signup` — IP-rate-limited (5/hour), optional email body, returns `rk_test_` key. Designed for first-five-minutes flow.
- **Admin:** `POST /v2/admin/keys` — bootstrap admin key required, can issue `rk_live_` keys with custom scopes/limits.

SDKs read `RABBIT_API_KEY` from env by default. Override per-call if needed.

### Versioning
- URL-versioned: `/v2/...`
- Breaking changes go to `/v3/...`. v2 stays supported ≥ 12 months after v3 GA.
- Additive changes (new fields, new endpoints) ship without version bump.

### Idempotency
Mutating endpoints (POST) accept `Idempotency-Key: <uuid>` header. Same key within 24h returns the original response. Required on `POST /v2/analyses` for production keys.

### Rate limiting and quotas
- Default: 60 requests/minute per key, sliding window
- Per-key concurrency cap on analyses: **3 in-flight by default** — exceeding returns 429 with `error.type = "too_many_in_flight_analyses"`
- Headers on every response:
  - `X-RateLimit-Limit`
  - `X-RateLimit-Remaining`
  - `X-RateLimit-Reset` (unix seconds)
- 429 response includes `Retry-After` (seconds)

### Touchpoint quota policy (v2.0)
- **v2.0: all keys unlimited** — `api_keys.touchpoints_processed` counter ticks for analytics, no enforcement
- v2.1: planned tiered limits + Stripe billing
- Hard per-dataset cap: 250,000 touchpoints (returns 413 at analysis time)

### Pagination
List endpoints use cursor pagination:
```
GET /v2/datasets?limit=20&cursor=eyJpZCI6...
```
Response:
```json
{ "data": [...], "next_cursor": "eyJpZCI6...", "has_more": true }
```

### Errors
All errors follow RFC 7807 Problem Details, extended with Stripe-grade fields for actionability:
```json
{
  "type": "https://docs.rabbit.dev/errors/dataset_not_ready",
  "code": "dataset_not_ready",
  "title": "Dataset not ready",
  "status": 409,
  "detail": "Dataset ds_abc123 is still validating.",
  "fix_hint": "Poll GET /v2/datasets/ds_abc123 until status=ready, or subscribe to the dataset.validated webhook.",
  "doc_url": "https://docs.rabbit.dev/errors#dataset_not_ready",
  "param": null,
  "instance": "/v2/analyses",
  "request_id": "req_01HXYZ..."
}
```

Field semantics:
- `code`: stable machine-readable string. **Never removed, only added.** SDKs switch on `code`.
- `fix_hint`: one-sentence corrective action when the fix is unambiguous.
- `param`: dotted path to offending field for `validation_failed` (e.g., `"models[2]"`).
- `doc_url`: deep link to that specific error in the docs.

Standard error codes (initial registry — see `docs/errors.md`):
- `unauthenticated` (401) — missing/invalid key
- `permission_denied` (403) — key lacks scope
- `not_found` (404)
- `validation_failed` (422) — request body schema error
- `dataset_not_ready` (409)
- `dataset_too_large` (413) — touchpoint count > 250k
- `too_many_in_flight_analyses` (429) — concurrency cap exceeded
- `rate_limited` (429) — request rate cap exceeded
- `idempotency_key_in_use` (409) — same key, different body within 24h
- `internal_error` (500)

### IDs
All resource IDs are prefixed:
- `ds_` dataset
- `an_` analysis
- `wh_` webhook
- `key_` API key
- `evt_` webhook event

Format: `<prefix>_<26-char-ULID>`.

---

## 2. Endpoints

### Health

#### `GET /v2/health`
No auth required. Returns `{ "status": "ok", "version": "2.0.0" }`.

---

### Datasets

#### `POST /v2/datasets`
Upload a dataset. Multipart form.

**Request:**
```
POST /v2/datasets
Content-Type: multipart/form-data
Authorization: Bearer rk_live_...

file=<csv|json|parquet>
name="Q2 2026 campaigns" (optional)
```

**Response 202:**
```json
{
  "id": "ds_01HXYZ...",
  "name": "Q2 2026 campaigns",
  "status": "validating",
  "filename": "campaigns.csv",
  "size_bytes": 4823901,
  "touchpoint_count": null,
  "created_at": "2026-05-12T10:00:00Z"
}
```

Validation runs as a background job. Poll `GET /v2/datasets/{id}` or subscribe to the `dataset.validated` webhook.

**Limits:**
- 500MB per file (enforced at edge via nginx `client_max_body_size`)
- **250,000 touchpoints per dataset** in v2.0 — upload accepted but analysis returns 413 if exceeded. Streaming/larger datasets land in v2.1.
- Larger files use signed-URL flow (see below).

#### `POST /v2/datasets/signed-url` *(M3+)*
Returns a presigned S3 URL for direct upload of large files.

#### `GET /v2/datasets/{id}`
**Response 200:**
```json
{
  "id": "ds_01HXYZ...",
  "status": "ready",
  "name": "Q2 2026 campaigns",
  "filename": "campaigns.csv",
  "size_bytes": 4823901,
  "touchpoint_count": 142503,
  "unique_customers": 28104,
  "schema_fingerprint": "sha256:...",
  "validation": {
    "errors": [],
    "warnings": [
      {
        "row": 42,
        "column": "conversion_value",
        "code": "negative_value_coerced",
        "message": "Negative value coerced to 0"
      }
    ]
  },
  "created_at": "2026-05-12T10:00:00Z",
  "ready_at": "2026-05-12T10:00:12Z"
}
```

Status values: `validating`, `ready`, `invalid`.

#### `GET /v2/datasets`
List datasets. Filters: `?status=ready&created_after=2026-01-01`.

#### `DELETE /v2/datasets/{id}`
Soft delete. Underlying analyses remain accessible.

---

### Analyses

#### `POST /v2/analyses`
Run one or many attribution models against a dataset.

**Request:**
```json
{
  "dataset_id": "ds_01HXYZ...",
  "models": ["linear", "time_decay", "first_touch", "last_touch", "position_based"],
  "options": {
    "time_decay_half_life_days": 7,
    "position_based_weights": { "first": 0.4, "last": 0.4, "middle": 0.2 },
    "conversion_window_days": 30
  },
  "webhook_id": "wh_01HXYZ..."
}
```

`models` accepts 1-5 values. `options` is optional and only applies to relevant models.

**As implemented (M3b, #17).** `webhook_id`, `Idempotency-Key` and `estimated_completion` are not built yet. The rest of the request is validated before anything is queued, and every failure is a 422 problem response:

| Field | Rule | `code` on failure |
|---|---|---|
| `models` | 1 to 5 registered model names, each at most once; the `models` array in responses keeps request order | `validation_failed` (empty or repeated), `too_many_models` (more than 5), `unknown_model` |
| `options.time_decay_half_life_days` | number > 0; default 7 | `validation_failed` |
| `options.position_based_weights` | `first`, `last` in [0, 1] with `first + last <= 1`; `middle` may be sent but must equal `1 - first - last`; default 0.4 / 0.4 | `validation_failed` |
| `options.conversion_window_days` | whole number of days from 1 to 3650 (the upper bound only guards against overflow); default: no window (every touchpoint is eligible, the v1 behaviour) | `validation_failed` |
| any other option key | rejected | `validation_failed` |

Options are validated even when no requested model uses them. Each result's `parameters` names the values that model actually used.

`conversion_window_days` is a lookback window in the sense of GA4's key event lookback window, which "determines how far back in time a touchpoint is eligible for attribution credit" ([GA4 attribution settings](https://support.google.com/analytics/answer/10597962)). Rabbit's models credit a whole journey as one path, so the window is anchored at the journey's last conversion event: touchpoints more than N days before it are removed before every model runs. Conversion events are always kept, so `total_conversions` and `total_revenue` do not change. GA4 applies a window per conversion; per-conversion windows would need per-conversion journeys, which v1 models do not have.

**Headers:**
```
Idempotency-Key: 8c4d...e7f
```

**Response 202:**
```json
{
  "id": "an_01HXYZ...",
  "status": "queued",
  "dataset_id": "ds_01HXYZ...",
  "models": ["linear", "time_decay", "first_touch", "last_touch", "position_based"],
  "created_at": "2026-05-12T10:05:00Z",
  "estimated_completion": "2026-05-12T10:05:30Z"
}
```

#### `GET /v2/analyses/{id}`
**Response 200 (running):**
```json
{
  "id": "an_01HXYZ...",
  "status": "running",
  "progress": { "models_completed": 2, "models_total": 5 }
}
```

**Response 200 (succeeded):**
```json
{
  "id": "an_01HXYZ...",
  "status": "succeeded",
  "dataset_id": "ds_01HXYZ...",
  "summary": {
    "total_conversions": 1842,
    "total_revenue": 284502.50,
    "unique_customers": 28104,
    "avg_journey_length": 4.2
  },
  "results": {
    "linear": {
      "channels": {
        "email":  { "credit": 0.32, "conversions": 589, "revenue": 91040.80, "confidence": 0.88 },
        "social": { "credit": 0.28, "conversions": 516, "revenue": 79660.70, "confidence": 0.81 }
      }
    },
    "time_decay": { "channels": { ... } },
    "first_touch": { "channels": { ... } },
    "last_touch": { "channels": { ... } },
    "position_based": { "channels": { ... } }
  },
  "comparison": {
    "channels": {
      "email": {
        "credit_by_model": { "linear": 0.32, "time_decay": 0.41, "first_touch": 0.55, "last_touch": 0.18, "position_based": 0.37 },
        "credit_spread": 0.37,
        "most_favorable_model": "first_touch",
        "least_favorable_model": "last_touch"
      }
    },
    "model_agreement_score": 0.62,
    "model_agreement_method": "jensen_shannon"
  },
  "started_at": "2026-05-12T10:05:02Z",
  "completed_at": "2026-05-12T10:05:24Z"
}
```

Status values: `queued`, `running`, `succeeded`, `failed`, `canceled`.

**As implemented (M3b, #17).** The worker runs the models in request order and commits `progress.models_completed` after each one, so a poll during a 5-model run sees 0, 1, ... 5. Each model's credits are the v1 `/attribution/analyze` credits for the same file and parameters. The `comparison` block is thin (C4): per channel only `credit_by_model`, `credit_spread`, `most_favorable_model` and `least_favorable_model`; conversions, revenue and parameters stay in `results`. Rules:

- `comparison.channels` has every channel that appears in any model's results, and `credit_by_model` has a key for every requested model. A model that gave a channel no credit shows `0.0` for it. Key order inside JSON objects is not significant (Postgres JSONB does not keep it); use the `models` array for order.
- `credit_spread` = max − min of that channel's `credit_by_model`.
- `most_favorable_model` / `least_favorable_model` are the models giving the channel the most / least credit; ties go to the model listed first in `models`.
- `comparison` is `null` for a single-model analysis (there is no pair to compare) and while the analysis is not `succeeded`.
- With no converting journeys, `comparison.channels` is `{}` and `model_agreement_score` is `null`.

Real output on the bundled `test_data.csv`, all five models with default options (credits rounded to 4 places here):

```json
"comparison": {
  "channels": {
    "email":       { "credit_by_model": { "linear": 0.3889, "time_decay": 0.3892, "first_touch": 0.3333, "last_touch": 0.6667, "position_based": 0.4667 },
                     "credit_spread": 0.3333, "most_favorable_model": "last_touch", "least_favorable_model": "first_touch" },
    "organic":     { "credit_by_model": { "linear": 0.2222, "time_decay": 0.2221, "first_touch": 0.3333, "last_touch": 0.3333, "position_based": 0.2667 },
                     "credit_spread": 0.1112, "most_favorable_model": "first_touch", "least_favorable_model": "time_decay" },
    "paid_search": { "credit_by_model": { "linear": 0.1944, "time_decay": 0.1946, "first_touch": 0.0, "last_touch": 0.0, "position_based": 0.1 },
                     "credit_spread": 0.1946, "most_favorable_model": "time_decay", "least_favorable_model": "first_touch" },
    "social":      { "credit_by_model": { "linear": 0.1944, "time_decay": 0.1941, "first_touch": 0.3333, "last_touch": 0.0, "position_based": 0.1667 },
                     "credit_spread": 0.3333, "most_favorable_model": "first_touch", "least_favorable_model": "last_touch" }
  },
  "model_agreement_score": 0.8832,
  "model_agreement_method": "jensen_shannon"
}
```

`most_favorable_model` names the rule under which a channel's credit share is largest. It is not a recommendation and says nothing about which model is correct or what a channel caused.

**`?include=journey` (C5).** `GET /v2/analyses/{id}?include=journey` adds a `journey` block with the v1 `JourneyAnalyzer` statistics for the whole uploaded dataset (no conversion window applied): `journey_lengths` (average, median, length buckets), `conversion_paths` (`top_paths` with frequency and percentage, `top_path_conversions_by_length`) and `time_to_conversion` (whole days from first touch to first conversion, average, median, buckets). The analyzer's generated `insights` strings are left out because they read as causal claims. The block is computed by the worker and is `null` before the analysis succeeds or when the dataset has no `customer_id` column. The analyzer counts `signup` and `subscribe` events as conversions as well as `conversion` and `purchase`, so its counts can differ from the models'. Without `include`, the response has no `journey` key; any other `include` value is a 422 `validation_failed`.

#### `GET /v2/analyses`
List, with filters: `?dataset_id=...&status=succeeded`.

#### `POST /v2/analyses/{id}/cancel`
Cancel a queued or running analysis.

---

### Webhooks

#### `POST /v2/webhooks`
**Request:**
```json
{
  "url": "https://customer.example.com/rabbit",
  "events": ["analysis.succeeded", "analysis.failed", "dataset.validated"],
  "description": "Production integration"
}
```

**Response 201:**
```json
{
  "id": "wh_01HXYZ...",
  "url": "https://customer.example.com/rabbit",
  "events": [...],
  "signing_secret": "whsec_...",
  "created_at": "..."
}
```

`signing_secret` is shown once. Subsequent GETs omit it.

#### Webhook delivery

Each delivery POSTs JSON with headers:
```
X-Rabbit-Event: analysis.succeeded
X-Rabbit-Delivery: evt_01HXYZ...
X-Rabbit-Signature: t=1715508000,v1=<hex hmac-sha256>
```

Signature input: `<timestamp>.<raw body>`. Customers verify using `signing_secret`.

Retry policy: 6 attempts at 1m, 5m, 30m, 2h, 12h, 24h. After exhaustion, webhook is auto-disabled.

#### `GET /v2/webhooks`, `GET /v2/webhooks/{id}`, `DELETE /v2/webhooks/{id}`

#### `GET /v2/webhooks/{id}/deliveries`
Recent delivery attempts with response codes and bodies (for debugging).

---

### Self-serve signup (DX1)

#### `POST /v2/keys/signup`
No auth. IP-rate-limited to 5/hour.

**Request (all fields optional):**
```json
{ "email": "dev@example.com", "use_case": "evaluating for our martech product" }
```

**Response 201:**
```json
{
  "id": "key_01HXYZ...",
  "key": "rk_test_a1b2c3...",
  "livemode": false,
  "rate_limit_per_minute": null,
  "created_at": "..."
}
```

`key` is shown once. Same response shape as `POST /v2/admin/keys` but always test-mode.

### Sample dataset (DX1)

#### `GET /v2/sample-dataset`
No auth. Returns a canned 200-row CSV. `Cache-Control: public, max-age=86400`. Lets devs run the full pipeline before they have their own data.

Bundled with the SDK as `rabbit.sample_dataset_path()`.

### Admin

#### `POST /v2/admin/keys`
Requires admin bootstrap key (env-configured). Issues a new API key.

**Request:**
```json
{
  "name": "Acme Corp prod",
  "scopes": ["datasets:write", "analyses:write", "webhooks:write"],
  "rate_limit_per_minute": 120
}
```

**Response 201:**
```json
{
  "id": "key_01HXYZ...",
  "key": "rk_live_a1b2c3...",
  "name": "Acme Corp prod",
  "scopes": [...],
  "created_at": "..."
}
```

`key` is shown once. Subsequent GETs return only the prefix (e.g., `rk_live_a1b2****`).

#### `GET /v2/admin/keys`, `DELETE /v2/admin/keys/{id}`

#### `GET /v2/admin/usage?key_id=...&from=...&to=...`
Returns call counts and touchpoints processed.

---

## 3. Resource model (Postgres)

```sql
api_keys (
  id ULID PK, key_hash, key_prefix, name, scopes JSONB,
  rate_limit_per_minute INT, created_at, revoked_at
)

datasets (
  id ULID PK, key_id FK, name, filename, storage_uri,
  size_bytes, touchpoint_count, unique_customers, schema_fingerprint,
  status ENUM, validation_report JSONB, created_at, ready_at, deleted_at
)

analyses (
  id ULID PK, key_id FK, dataset_id FK, models JSONB, options JSONB,
  status ENUM, progress JSONB, results JSONB, comparison JSONB,
  idempotency_key TEXT,
  last_progress_at TIMESTAMPTZ,   -- heartbeat for janitor (T2)
  webhook_id FK NULL,
  created_at, started_at, completed_at, error JSONB,
  UNIQUE (key_id, idempotency_key)  -- A2: idempotency truth in Postgres
)

webhooks (
  id ULID PK, key_id FK, url, events JSONB,
  signing_secret_ciphertext BYTEA,  -- encrypted with libsodium SecretBox; key from RABBIT_WEBHOOK_SECRET_KEY env
  signing_secret_prefix TEXT,        -- first 8 chars of plaintext, shown in GET for identification
  enabled BOOL, created_at, last_delivery_at
)

webhook_deliveries (
  id ULID PK, webhook_id FK, event_type, payload JSONB,
  response_code, response_body, attempt INT, succeeded BOOL,
  delivered_at, next_retry_at
)

audit_log (
  id ULID PK, key_id FK, action, resource_type, resource_id,
  request_id, ip, user_agent, created_at
)
```

---

## 4. SDK surface (Python, M4)

```python
from rabbit import Rabbit

client = Rabbit(api_key="rk_live_...")

# Upload
dataset = client.datasets.create(file=open("campaigns.csv", "rb"))
dataset = client.datasets.wait_until_ready(dataset.id, timeout=60)

# Analyze
analysis = client.analyses.create(
    dataset_id=dataset.id,
    models=["linear", "time_decay", "first_touch", "last_touch", "position_based"],
)
result = client.analyses.wait_until_done(analysis.id, timeout=120)

# Compare
print(result.comparison.model_agreement_score)
for channel, data in result.comparison.channels.items():
    print(channel, data.credit_spread, data.most_favorable_model)
```

Quickstart target: 8 lines from `pip install` to first comparison result.

---

## 5. Backward compatibility

- `/v1/*` endpoints remain mounted, unchanged, until v2.1
- Frontend stays on `/v1/*` through M5
- README's curl example updates to `/v2/...` at M5

---

## 6. Validation error schema (typed)

```python
class ValidationIssue(BaseModel):
    row: int | None          # null when issue is dataset-wide
    column: str | None       # null when issue is row-wide
    code: str                # stable machine-readable code, e.g. "negative_value_coerced"
    message: str             # human-readable

class ValidationReport(BaseModel):
    errors: list[ValidationIssue]
    warnings: list[ValidationIssue]
```

Stable codes (initial set; never removed, only added):
- `missing_required_column`
- `invalid_timestamp_format`
- `negative_value_coerced`
- `duplicate_row_dropped`
- `unknown_channel_normalized`
- `invalid_numeric_format` — the existing validator found a non-numeric value.
- `invalid_file_format` — the uploaded CSV, JSON, or Parquet file could not be parsed.

## 7. Comparison math (`model_agreement_score`)

`model_agreement_score` is the **mean pairwise Jensen-Shannon divergence** across all model pairs, inverted and normalized so 1.0 = perfect agreement, 0.0 = maximum disagreement.

Each model's per-channel credits form a probability distribution P over channels (sums to 1.0). For N models there are N(N-1)/2 pairs. For each pair (P, Q):

```
M = 0.5 * (P + Q)
JSD(P, Q) = 0.5 * KL(P || M) + 0.5 * KL(Q || M)    # bounded [0, log 2]
```

Normalize: `jsd_norm = JSD / log(2)` → [0, 1].
Agreement: `1.0 - mean(jsd_norm over pairs)` → [0, 1].

Why not cosine similarity: credit vectors lie on the probability simplex (∑=1), so they all have the same direction-magnitude relationship. Cosine collapses meaningful differences.

### Definitions as implemented (M3b, #17)

The formula above leaves a few choices open. Each is resolved by the standard definition, with its source; the code is `src/v2/comparison.py`.

1. **Log base 2.** `JSD / ln 2` with natural logs equals JSD computed directly with base-2 logs, so the implementation uses `log2` and needs no separate normalization step. With base 2 the divergence of two distributions is bounded by 1 (Lin 1991, the paper that introduced the measure; general bound `log_b 2`), so `jsd_norm` ∈ [0, 1] and agreement ∈ [0, 1].
2. **Divergence, not distance.** `model_agreement_score` uses the divergence itself. The *Jensen-Shannon distance* is its square root, a metric (Endres & Schindelin 2003); SciPy's `scipy.spatial.distance.jensenshannon` returns that distance ("the square root of the Jensen-Shannon divergence"), so a SciPy cross-check has to square it. The tests do exactly that.
3. **Channels missing from a model are 0 credit.** All models in one analysis are compared over the union of their channels; a channel a model did not credit is a 0 entry. Terms with `p = 0` contribute `0 · log(0 / m) = 0` by the information-theory convention `0 log 0 = 0` (Cover & Thomas 2006, §2.1 and §2.3). Because `M = (P + Q) / 2` is positive wherever P or Q is, `KL(P || M)` is always finite, which is why JSD, unlike KL, needs no smoothing for zero credits.
4. **Normalization.** Each model's credits are divided by their total before comparison, as SciPy does ("will normalize p and q if they don't sum to 1.0"). Credits already sum to 1 up to float rounding; this keeps rounding from pushing the result outside [0, 1]. The result is also clamped to [0, 1] for the same reason.
5. **Pairs and the mean.** All `N(N-1)/2` unordered pairs, unweighted arithmetic mean, `model_agreement_score = 1 - mean`. JSD is symmetric, so pair order does not matter.
6. **Edge cases.** One model: no pairs, so `comparison` is `null` (an agreement score of 1.0 would claim an agreement that was never tested). No converting journeys: every model's credit total is 0, which is not a probability distribution, so `model_agreement_score` is `null` and `channels` is `{}`. Negative, NaN or infinite credit raises an error rather than producing a score.

Worked values (hand-computed in [`tests/v2/golden/jsd_golden.json`](../../tests/v2/golden/jsd_golden.json)):

| Case | P | Q | JSD (bits) |
|---|---|---|---:|
| identical | any | same | 0 |
| fully disjoint | `{email: 1}` | `{social: 1}` | 1 |
| one shared channel | `{email: .5, social: .5}` | `{social: .5, organic: .5}` | 0.5 |
| subset | `{email: .5, social: .5}` | `{email: 1}` | 1.5 − 0.75·log2 3 ≈ 0.311278 |

Three models `first_touch {social: 1}`, `last_touch {email: 1}`, `linear {social: .5, email: .5}` give pair JSDs 1, 0.311278, 0.311278, so agreement = 0.5·log2 3 − 1/3 ≈ 0.459148. All five models on `test_data.csv` give 0.8832 (recorded, cross-checked against SciPy).

`model_agreement_score` measures how similarly the named rule-based models split credit on this dataset. High agreement means the model choice matters little for this data; it does not mean the shared answer is right, and none of the models estimates causal effect.

Sources:
- J. Lin, "Divergence measures based on the Shannon entropy," *IEEE Transactions on Information Theory* 37(1):145–151, 1991. doi:10.1109/18.61115
- D. M. Endres and J. E. Schindelin, "A new metric for probability distributions," *IEEE Transactions on Information Theory* 49(7):1858–1860, 2003. doi:10.1109/TIT.2003.813506
- T. M. Cover and J. A. Thomas, *Elements of Information Theory*, 2nd ed., Wiley, 2006, §2.1 (entropy, `0 log 0 = 0`) and §2.3 (relative entropy).
- SciPy, [`scipy.spatial.distance.jensenshannon`](https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.distance.jensenshannon.html) (returns the distance; `base` argument; normalizes inputs).

## 8. Open questions

- [ ] S3 vs Cloudflare R2 for object storage (defer; abstraction in place)
- [ ] Should webhook signature use stripe-style `Stripe-Signature` format or our own? Stripe-style for familiarity.
- [ ] Confidence scoring: keep current heuristic or rebuild on bootstrapping? Defer to v2.1.
- [ ] Add `dry_run: true` on `POST /v2/analyses` to estimate cost/time without running? Nice-to-have for v2.1.
