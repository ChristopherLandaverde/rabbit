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

## 8. Open questions

- [ ] S3 vs Cloudflare R2 for object storage (defer; abstraction in place)
- [ ] Should webhook signature use stripe-style `Stripe-Signature` format or our own? Stripe-style for familiarity.
- [ ] Confidence scoring: keep current heuristic or rebuild on bootstrapping? Defer to v2.1.
- [ ] Add `dry_run: true` on `POST /v2/analyses` to estimate cost/time without running? Nice-to-have for v2.1.
