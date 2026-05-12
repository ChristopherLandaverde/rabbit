# Rabbit v2 — Execution Plan

**Companion to:** [ROADMAP.md](./ROADMAP.md) and [SPEC_v2.md](../api/SPEC_v2.md)
**Approach:** Tracer-bullet vertical slices. Every milestone ends with a working end-to-end demo.
**Branching:** Feature branches off `main`, PR per milestone, merge behind a `RABBIT_V2_ENABLED` env flag until M5.
**Timeline:** **6-8 weeks full-time** (re-baselined from initial 3-4 week estimate after eng review — six discrete infra additions + security review + SDK + docs realistically requires this).

## DX review adjustments (applied)

ICP confirmed: **developers building marketing tools**. Target DX tier: **Champion (< 2 min TTHW)**. The following came out of `/plan-devex-review`:

- **DX1** Self-serve key issuance: `POST /v2/keys/signup` (IP rate-limited, returns `rk_test_` key, optional email capture). Minimal landing page form. Removes the manual-issuance email-someone blocker.
- **DX1** Sample dataset bundled: `examples/sample_campaigns.csv` (200 deterministic rows) ships in SDK and at `GET /v2/sample-dataset`. Devs can call the API without their own data.
- **DX1** Hosted API explorer: `docs/playground/` with prefilled test key, curl button, runs against prod API with `rk_test_`. Pretty-printed JSON response inline.
- **DX2** SDK design pulled forward to **M2** (prototype quickstart against datasets API), real publishing stays M4. Catches awkward API shapes before freeze.
- **DX3** Error schema upgraded to Stripe-grade. Every problem response includes: `type` (URL), `code` (stable string), `title`, `detail`, `fix_hint` (optional), `param` (optional, for validation_failed), `doc_url`. Error code registry committed at `docs/errors.md`.
- **DX4** M5 docs ships **3 recipes** alongside reference: (1) Next.js dashboard integration, (2) weekly Slack report cron, (3) 5-model comparison walkthrough. Each is copy-paste-runnable against the sample dataset.
- **DX5** Deprecation policy: `Sunset:` and `Deprecation:` HTTP headers on v1 endpoints at GA per RFC 8594. `CHANGELOG.md` has explicit "Migration from v1" section.
- **DX6** Environment conventions: SDK reads `RABBIT_API_KEY` env var by default. `docs/recipes/github-actions.md` snippet. Test-mode (`rk_test_`) explicitly: no rate limit, unlimited touchpoints, data isolated from live keys, `is_test` flag on every resource.
- **DX7** `rabbit-examples/` repo created at M5 with the 3 recipes as runnable code. Issue templates (`bug.yml`, `feature.yml`), `CONTRIBUTING.md`, Discord invite in README.
- **DX8** TTHW instrumentation: `api_keys.first_dataset_at`, `first_analysis_at`, `first_succeeded_at` columns. `GET /v2/admin/funnel` reports activation funnel and median TTHW.

## Eng review adjustments (applied)

The following decisions came out of `/plan-eng-review` and are reflected in milestones below and in [SPEC_v2.md](../api/SPEC_v2.md):

- **A1 (P0)** Webhook signing secret is **encrypted at rest** (libsodium secretbox with key from env / KMS), not hashed. Worker decrypts at sign-time. *Hashed secrets cannot sign.*
- **A2 (P1)** Idempotency persisted in Postgres via unique index `(key_id, idempotency_key)` on `analyses`. Redis is optional cache, not source of truth.
- **A3** Drop arq from v2.0. Use FastAPI `BackgroundTasks` + Postgres-as-queue (`SELECT FOR UPDATE SKIP LOCKED` worker loop). Re-introduce arq in v2.1 if scheduled jobs or cross-process fan-out actually needed.
- **A4** Per-key `max_concurrent_analyses` (default 3); enforced at `POST /v2/analyses` — return 429 with structured error if exceeded.
- **A5** Object storage path scheme: `{key_id}/{dataset_id}.{ext}`. Worker enforces key-scoped reads; no cross-tenant access path.
- **A6** Custom `/v2/openapi.json` endpoint scoped to v2 routes only. Disable global `/openapi.json` (`app.openapi_url=None`).
- **C1** `model_agreement_score` uses **Jensen-Shannon divergence**, not cosine similarity. Credit vectors live on the probability simplex; cosine is meaningless there. JSD is bounded [0,1], symmetric, and interpretable.
- **C2** `ValidationError` and `ValidationWarning` are typed pydantic models with `row`, `column`, `code`, `message`. JSONB at the column, typed at the API.
- **C3** v2.0 quota policy: **all keys unlimited, monitoring only**. `api_keys.touchpoints_processed` counter ticks but no enforcement until v2.1. Documented explicitly in spec.
- **C4** Comparison response: per-channel `credit_by_model` keys reference channel names already in `results`. SDK joins. Avoids ~2x payload bloat at scale.
- **C5** `src/core/journey_analysis.py` exposed as optional `journey` block in analysis response when `?include=journey`. Avoids dead code drift.
- **T1-T4** Critical tests added to M3/M4 task lists below.
- **Perf1** v2.0 touchpoint cap: **250,000 rows per dataset**. Documented limit, returned as 413 on upload if exceeded.
- **Perf2** File-size enforcement at nginx/edge (`client_max_body_size 500M`), not just in app code.

---

## Tech stack additions

| Concern | Choice | Why |
|---|---|---|
| DB | Postgres 16 | Boring, JSONB for results, ULID via extension |
| Migrations | Alembic | Already in FastAPI ecosystem |
| Cache + queue | Redis 7 | Rate limit + job broker, single dep |
| Job framework | **FastAPI BackgroundTasks + Postgres queue** | Most analyses < 60s; arq deferred to v2.1 (A3) |
| Object storage | S3-compatible (boto3) | R2 in prod, MinIO in local docker-compose |
| ULID | `python-ulid` | Sortable IDs |
| HTTP auth | Custom FastAPI dependency | Don't pull in fastapi-users |
| SDK gen | `openapi-python-client` + hand-tuned wrapper | Generated core, ergonomic top layer |
| Docs site | Mintlify (free tier) or Docusaurus | Mintlify if hosted, Docusaurus if self-hosted |
| Hosting (preview) | Fly.io | Scale-to-zero, simple Postgres add-on |

---

## M0 — Foundation (Days 1-3)

### Tasks
- [ ] Add Postgres + Redis + MinIO services to `docker-compose.yml`
- [ ] Add deps: `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `redis`, `boto3`, `python-ulid`, `pynacl` (libsodium for webhook secret encryption)
- [ ] Create `src/db/` package: engine, session, base model
- [ ] Init Alembic, create migration `0001_v2_foundation.py` for all tables in SPEC §3
- [ ] Mount v2 router: `app.include_router(v2_router, prefix="/v2")` — empty except health
- [ ] Add `RABBIT_V2_ENABLED` env flag; v2 router is no-op when false
- [ ] Update `src/main.py` lifespan to manage DB pool + Redis client
- [ ] CI: add `pytest tests/v2/` matrix; spin up Postgres in GH Actions

### Verification
- `docker-compose up` brings up 5 services healthy
- `alembic upgrade head` succeeds
- `curl /v1/health` and `curl /v2/health` both return 200
- All existing v1 tests still pass

---

## M1 — Auth & Tenancy (Days 4-6)

### Tasks
- [ ] `src/v2/auth/` package: `ApiKey` model, key generation (`rk_live_` / `rk_test_` + 32-byte base62), hashing (Argon2id), prefix storage for display
- [ ] FastAPI dependency `require_api_key` — extracts bearer, looks up hash, attaches `ApiKey` (with `is_test` flag) to request state
- [ ] Scope check dependency `require_scope("datasets:write")`
- [ ] Rate limiter: Redis sliding window keyed by `key_id`; middleware adds `X-RateLimit-*` headers. **Test-mode keys bypass rate limit and quota.**
- [ ] `POST /v2/admin/keys`, `GET /v2/admin/keys`, `DELETE /v2/admin/keys/{id}` — gated by `ADMIN_BOOTSTRAP_KEY` env
- [ ] **`POST /v2/keys/signup`** (DX1): IP rate-limited (5/hour), optional email body, returns `rk_test_` key with `scopes=["datasets:write", "analyses:write"]`, no admin required
- [ ] **Funnel columns** (DX8) on `api_keys`: `first_dataset_at`, `first_analysis_at`, `first_succeeded_at`; updated by middleware/worker on first occurrence
- [ ] Audit log writer: middleware logs every mutating request
- [ ] Tests: valid key 200, missing key 401, bad key 401, wrong scope 403, live key rate-limited at 429, test key NOT rate-limited, signup endpoint IP-rate-limited at 5/hour, funnel timestamp set exactly once

### Verification
Demo script: bootstrap admin key from env, issue a test key, call it 70 times in a minute, observe 429 after 60.

---

## M2 — Datasets API (Days 7-9)

### Tasks
- [ ] `src/v2/storage/` interface: `put(key, bytes)`, `get(key)`, `delete(key)`, `signed_url(key, ttl)` — S3 impl + local-disk impl
- [ ] `POST /v2/datasets` — multipart receive, write to storage, insert row with `status=validating`, enqueue validation job
- [ ] **`GET /v2/sample-dataset`** (DX1): returns canned `examples/sample_campaigns.csv` (200 rows, deterministic). No auth required. Cacheable.
- [ ] **SDK quickstart prototype** (DX2): hand-write `examples/quickstart.py` (8 lines from SPEC §4) against the M2 datasets endpoints. Run it. Note any awkward shapes — fix the API now, not at M4.
- [ ] Validation job (arq): re-uses existing `src/core/validation/` to read file, count touchpoints, detect schema, write validation_report
- [ ] `GET /v2/datasets/{id}`, `GET /v2/datasets`, `DELETE /v2/datasets/{id}`
- [ ] Cursor pagination helper (`src/v2/pagination.py`)
- [ ] RFC 7807 error response renderer (`src/v2/errors.py`)
- [ ] Tests: upload happy path, invalid file → status=invalid with error report, pagination, scope enforcement, delete

### Verification
End-to-end: upload `test_data.csv`, poll until `status=ready`, validation report includes touchpoint count.

---

## M3 — Async Analyses + Comparison (Days 10-13)

### Tasks
- [ ] `POST /v2/analyses` — validate dataset is ready, validate models[] against registered models, check concurrency cap (A4), upsert by `(key_id, idempotency_key)` unique index (A2), enqueue worker
- [ ] Worker loop (BackgroundTasks-backed; Postgres `SELECT FOR UPDATE SKIP LOCKED` for safety with multiple processes):
  - Loads dataset from storage (validates key_id matches storage path prefix per A5)
  - Iterates `models[]`, runs each via existing `AttributionFactory`
  - Updates `progress` after each model completes; writes heartbeat `last_progress_at` for janitor (T2)
  - Computes `comparison` block: credit_by_model per channel, credit_spread, most/least favorable, `model_agreement_score` via **Jensen-Shannon divergence** mean over pairwise model distributions (C1)
  - Writes thin `comparison` (channel keys, not duplicated credits — C4); full `results` retained
  - Enqueues webhook delivery if `webhook_id` provided
- [ ] Touchpoint cap: reject analysis at POST if `dataset.touchpoint_count > 250_000` → 413 (Perf1)
- [ ] Janitor job: marks `status=failed` with error `worker_timeout` if `started_at + max_runtime_minutes < now` and no heartbeat (T2)
- [ ] `GET /v2/analyses/{id}`, `GET /v2/analyses`, `POST /v2/analyses/{id}/cancel`
- [ ] **JSD math golden file** (T4): hand-compute 3 cases (identical models → JSD=0, fully disjoint → JSD=1, partial overlap → known value). Property test: JSD ∈ [0,1] for any input.
- [ ] Tests: single-model analysis, 5-model analysis with comparison, idempotency replay returns same `analysis_id`, concurrency cap → 429, cancel running, dataset_not_ready 409, touchpoint-cap 413, worker-crash recovery (T2), p95 latency budget on 10K-row fixture

### Verification
Curl uploads dataset, posts analysis with all 5 models, polls completion in <30s on 10K touchpoints, response includes comparison block with model_agreement_score.

---

## M4 — Webhooks + Python SDK (Days 14-17)

### Tasks (webhooks)
- [ ] `POST /v2/webhooks`, `GET`, `DELETE` endpoints
- [ ] Webhook secret: generate on create, return plaintext **once**, store as `signing_secret_ciphertext` encrypted via `pynacl.SecretBox` with key from `RABBIT_WEBHOOK_SECRET_KEY` env (A1)
- [ ] Delivery worker: decrypts secret, signs payload with HMAC-SHA256 (`t=<ts>,v1=<hex>`), POSTs, records delivery, retries per schedule
- [ ] Auto-disable after 6 failed attempts; surface via webhook GET
- [ ] `GET /v2/webhooks/{id}/deliveries`
- [ ] **Replay attack rejection** (T1): customer-side verification doc + server-side test that signatures older than 5 min are rejected by reference verifier
- [ ] Tests: encrypted-secret roundtrip, signature verification roundtrip, replay rejection (T1), retry schedule (clock fixture), auto-disable, scope enforcement, customer endpoint returning 5xx triggers retry, **DELETE dataset preserves analyses** regression test (T3)

### Tasks (SDK)
- [ ] New repo `rabbit-python-sdk` or `sdk/python/` in this repo (decision: monorepo for now)
- [ ] Generate base client from `/v2/openapi.json` with `openapi-python-client`
- [ ] Hand-tuned wrapper `rabbit/__init__.py`: `Rabbit`, `client.datasets.*`, `client.analyses.*`, `wait_until_ready`, `wait_until_done` helpers
- [ ] Type hints + docstrings everywhere
- [ ] pytest + recorded HTTP fixtures (vcrpy or pytest-httpx)
- [ ] CI: publish to TestPyPI on tag

### Verification
8-line quickstart from SPEC §4 runs against local server end-to-end.

---

## M5 — Docs, Hosting, Launch (Days 18-21)

### Tasks (docs)
- [ ] Docs site scaffold (Mintlify recommended); pages: Quickstart, Auth, Datasets, Analyses, Webhooks, SDK, Errors, Changelog
- [ ] **`docs/playground/`** (DX1): hosted API explorer page with prefilled `rk_test_` key, curl button per endpoint, pretty-printed JSON inline response. Calls prod API. Magical-moment delivery vehicle.
- [ ] **`docs/recipes/`** (DX4): 3 copy-paste-runnable recipes against sample dataset:
  - `nextjs-dashboard.md` — embed attribution widget
  - `slack-weekly-report.md` — cron job posting top-channel report
  - `model-comparison.md` — interpret the comparison block
- [ ] **`docs/errors.md`** (DX3): error code registry. Every code documented with cause + fix.
- [ ] **`docs/recipes/github-actions.md`** (DX6): CI snippet using `RABBIT_API_KEY` env var
- [ ] **Sample CSV** (DX1) committed at `examples/sample_campaigns.csv` and bundled in SDK package data
- [ ] **`rabbit-examples/` repo** (DX7): 3 recipes as runnable code, MIT license, README with one-command run
- [ ] **Issue templates + CONTRIBUTING.md** (DX7) at repo root: `.github/ISSUE_TEMPLATE/bug.yml`, `feature.yml`, `CONTRIBUTING.md`
- [ ] **Deprecation headers** (DX5): v1 endpoints return `Deprecation: true` and `Sunset: <RFC1123 date>` headers at GA per RFC 8594. `CHANGELOG.md` "Migrating from v1" section.
- [ ] **TTHW dashboard query** (DX8): `GET /v2/admin/funnel?from=...&to=...` returns activation funnel counts and median TTHW (time from key issuance to first successful analysis)
- [ ] Runnable code blocks (curl + Python tabs)
- [ ] Publish OpenAPI at `/v2/openapi.json`; embed Swagger UI at `/v2/docs`
- [ ] Postman collection committed at `docs/api/rabbit-v2.postman.json`
- [ ] `CHANGELOG.md` started; v2.0.0 entry
- [ ] Update root `README.md` with v2 quickstart at top, v1 demo moved to bottom

### Tasks (hosting)
- [ ] `fly.toml` for API; Fly Postgres + Upstash Redis
- [ ] R2 bucket for storage
- [ ] Health check + auto-rollback on deploy
- [ ] Status page (Better Stack free tier) wired to `/v2/health`
- [ ] Free tier: rate-limited keys self-serve via simple landing page (manual issuance acceptable at launch)

### Tasks (launch)
- [ ] Flip `RABBIT_V2_ENABLED=true` in prod
- [ ] Soft launch: post in r/marketing, r/analytics, IndieHackers, Hacker News (Show HN)
- [ ] Onboard 3 design-partner devs from network; gather feedback in shared doc

### Verification
Public URL serves docs + API. README quickstart works copy-paste. Status page green for 7 days.

---

## Cross-cutting

### Testing strategy
- Unit tests stay in `tests/unit/`
- v2 integration tests in `tests/v2/` — spin up Postgres + Redis + MinIO via testcontainers
- Contract tests: golden files for analysis results to prevent regression in math
- Load test M3 endpoint with locust on 100K-row fixture before M5

### Observability (lightweight at launch)
- Structured logs (existing) include `request_id`, `key_id`, `analysis_id`
- Prometheus metrics: request count/latency, queue depth, job duration, webhook success rate
- Sentry for error tracking (free tier)

### Security checklist before M5
- [ ] Re-run `eb433d7` security audit on v2 surface
- [ ] Verify rate limit can't be bypassed (no key, expired key, revoked key)
- [ ] File upload size + MIME enforced server-side
- [ ] No PII in logs (touchpoint data only logged as counts)
- [ ] HTTPS-only cookie/header settings
- [ ] CORS for v2: tight allowlist, not `*`
- [ ] Dependabot enabled

### Decision log
Decisions captured in `docs/technical/decisions/` as numbered ADRs (`0001-postgres-over-sqlite.md`, etc.) as they're made.

---

## NOT in scope for v2.0 (deferred to v2.1+)

| Item | Why deferred |
|---|---|
| JS/TS SDK | Ship Python first, validate API ergonomics with real integrations |
| arq / scheduled jobs | Not needed for short async analyses; BackgroundTasks + Postgres queue covers v2.0 |
| Billing / Stripe / quota enforcement | v2.0 = unlimited keys, monitor only. Pricing decision needs usage data |
| Touchpoint streaming / polars chunked reads | Honest scaling cliff at 250K rows; document the cap, build streaming when usage demands |
| Data connectors (Snowflake/BigQuery/S3 ingest) | Path B feature; v2.0 stays file-upload only |
| SSO / RBAC / multi-region | Enterprise concerns; out of ICP |
| Custom attribution models (user-defined weights) | Position-based already accepts weights; full custom waits for demand |
| Frontend rewrite on v2 | React app stays on `/v1/*` through GA; migrate as v2.1 effort |
| Webhook delivery beyond 6 retries / 39h | Stripe-style 3-day retry can wait; current schedule covers transient failures |
| JSONB result row-size monitoring + columnar split | Perf3 — profile after launch, split only if median row > 256KB |

## What already exists (reuse, don't rebuild)

| Existing module | v2 reuse plan |
|---|---|
| `src/core/attribution/` factory + 5 model implementations | **Reused as-is** by worker in M3. No changes. |
| `src/core/validation/validators.py` | **Reused** by dataset validation job in M2 (wrapped in typed pydantic surface per C2). |
| `src/core/confidence.py` | **Reused** for per-channel `confidence` field in results. |
| `src/core/journey_analysis.py` | **Surfaced** as optional `journey` block in `GET /v2/analyses/{id}?include=journey` (C5). |
| `src/core/security.py` middleware | **Reused** for security headers; v2 auth dependency is additive. |
| `src/core/monitoring.py` health checker | **Reused** by `/v2/health` + Prometheus metrics endpoint. |
| `src/models/` pydantic models | **Reused** as internal types; v2 wraps them in API-facing schemas. |
| `tests/unit/`, `tests/integration/` | **Kept**; `tests/v2/` is additive (testcontainers-based). |

## Worktree parallelization strategy

| Step | Modules touched | Depends on |
|---|---|---|
| M0 foundation | `src/db/`, `docker-compose.yml`, `alembic/` | — |
| M1 auth | `src/v2/auth/`, `src/v2/admin/` | M0 |
| M2 datasets | `src/v2/datasets/`, `src/v2/storage/` | M0, M1 (auth dependency) |
| M3 analyses | `src/v2/analyses/`, worker loop | M0, M1, M2 |
| M4a webhooks | `src/v2/webhooks/` | M1, M3 |
| M4b SDK | `sdk/python/` (separate package dir) | M0-M3 stable OpenAPI |
| M5 docs+hosting | `docs/`, `fly.toml`, status page | All |

**Parallel lanes:**
- **Lane A (sequential, backend core):** M0 → M1 → M2 → M3
- **Lane B (joins at M3 done):** M4a webhooks
- **Lane C (joins at M3 done):** M4b SDK — different worktree, different package dir
- **Lane D (final):** M5

Realistic execution: Lane A is the critical path. Lanes B and C launch in parallel worktrees once M3 lands. Conflict risk: low — webhooks/SDK touch disjoint modules. SDK consumer feedback can still flag API shape issues during M4b; budget 1-2 days of M3 rework if so.

## Failure modes (critical gaps to ensure handled)

| Codepath | Realistic failure | Plan handles? |
|---|---|---|
| Worker crash mid-analysis | Status stuck at `running` forever | ✅ Janitor + heartbeat (T2) |
| Webhook customer endpoint 5xx | Lost notification | ✅ Retry schedule + auto-disable |
| Webhook signature replay | Attacker replays valid signature | ✅ Timestamp window check (T1) |
| DELETE dataset while analysis pending | Analysis worker reads missing file | ⚠ Spec says "soft delete"; M2 task must enforce storage retention until all analyses complete |
| Idempotency-Key collision across keys | Wrong customer's result returned | ✅ Composite unique index `(key_id, idempotency_key)` (A2) |
| Touchpoint count > worker memory | OOM kill | ✅ 250K cap returned 413 at POST (Perf1) |
| Redis down | Rate limit bypass, idempotency cache miss | ⚠ Acceptable: rate limit fails open (log), idempotency falls back to Postgres unique index |
| Encrypted secret key rotation | Old webhooks can't sign | ⚠ Out of v2.0 scope; document as known limitation |

## Definition of Done for v2.0 GA

- All M0-M5 verification steps pass
- 90%+ test coverage on `src/v2/`
- p95 < 30s for 10K-touchpoint 5-model analysis
- README quickstart works against hosted URL
- Python SDK installable from PyPI
- One real external developer has integrated end-to-end and reported back
- `CHANGELOG.md` tagged `v2.0.0`

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 15 issues found, 15 incorporated, 0 critical gaps unaddressed |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | n/a (backend plan) |
| DX Review | `/plan-devex-review` | Developer experience gaps | 1 | CLEAR (PLAN) | 8 dimensions scored, 8 fixes incorporated, TTHW 30min→<2min (Champion tier) |

### DX Scorecard

| Dimension | Before | After (planned) | Notes |
|---|---|---|---|
| Getting Started | 3/10 | 9/10 | Self-serve signup + sample dataset + playground |
| API/CLI/SDK design | 7/10 | 9/10 | SDK prototype pulled to M2; test-mode keys defined |
| Error messages | 6/10 | 9/10 | Stripe-grade schema with code + fix_hint + doc_url |
| Documentation | 6/10 | 8/10 | 3 recipes + error registry + playground |
| Upgrade path | 7/10 | 9/10 | RFC 8594 Sunset headers + migration guide |
| Dev environment | 5/10 | 8/10 | RABBIT_API_KEY convention, GH Actions snippet, test mode |
| Community | 4/10 | 7/10 | examples repo + issue templates + CONTRIBUTING |
| DX Measurement | 3/10 | 8/10 | Funnel columns + /v2/admin/funnel endpoint |
| **TTHW target** | **~30 min** | **< 2 min** | **Champion tier** |
| **Overall DX** | **4.4/10** | **8.4/10** | |

- **UNRESOLVED:** 0
- **VERDICT:** ENG + DX CLEARED — plan reflects all accepted findings. Recommended next: `/to-issues` to break into GitHub issues, then start M0.

### Eng review summary (this session)

- **Scope challenge:** Complexity check triggered (50+ files / 6 infra additions). Decided: keep scope, re-baseline timeline from 3-4 weeks to **6-8 weeks** full-time.
- **Architecture:** 6 findings, all incorporated. P0 webhook secret bug fixed in SPEC §3.
- **Code quality:** 5 findings, all incorporated. JSD replaces cosine for `model_agreement_score` (SPEC §7 new).
- **Tests:** 4 critical gaps added (replay attack, worker crash, DELETE preservation, JSD golden file).
- **Performance:** 2 findings — 250K touchpoint cap declared; nginx edge size enforcement.
- **Failure modes flagged:** 2 ⚠ items (DELETE storage retention timing, encrypted-secret rotation) documented as known limitations or M2 task requirements.
- **NOT in scope:** 10 explicit deferrals listed.
- **Parallelization:** Lane A backend sequential (M0→M3), Lanes B/C parallel (webhooks + SDK) after M3, Lane D docs/hosting last.

