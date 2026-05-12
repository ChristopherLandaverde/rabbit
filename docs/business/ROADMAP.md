# Rabbit Roadmap — v2 to Viable API

**Updated:** 2026-05-12
**Target path:** Developer API SaaS (Path A)
**ICP:** Developers building marketing tools — agencies, martech vendors, analytics platforms embedding attribution
**Budget:** Full-time push, ~3-4 weeks to v2.0 GA

---

## North Star

> A developer can `pip install rabbit-sdk`, paste an API key, push a dataset, and get attribution results from 5 models — including a side-by-side comparison — in under 10 minutes.

## What "viable" means for this ICP

Developers buying a marketing API care about:

1. **API quality** — predictable schemas, versioned, OpenAPI 3.1, idempotency keys
2. **SDK** — at minimum Python; JS/TS soon after
3. **Async by default** — large datasets without timeouts; webhooks or polling
4. **Comparison** — one call, N models, structured diff (the differentiator)
5. **Trust** — auth, rate limits, error codes, status page, changelog
6. **Docs** — copy-paste examples, runnable in 60 seconds

The current v1 fails on every one of these except a thin slice of #1.

---

## Milestones

### M0 — Foundation (Week 0, ~3 days)
**Goal:** Make the codebase ready for the v2 surface without breaking v1 demos.

- Postgres + Alembic migrations wired into Docker Compose
- Redis added for jobs + rate limits
- `Dataset`, `Analysis`, `ApiKey`, `Webhook` table schemas
- Versioned routing: `/v1/*` (legacy) and `/v2/*` (new)
- Stub OpenAPI spec generator with `x-rabbit-*` extensions for SDK gen

**Exit:** `docker-compose up` boots API + Postgres + Redis; v1 endpoints unchanged; `/v2/health` returns 200.

### M1 — Auth & Tenancy (Week 1, ~3 days)
**Goal:** Every v2 request authenticated and rate-limited.

- API key issuance via `POST /v2/admin/keys` (bootstrap key from env)
- `Authorization: Bearer rk_live_...` middleware
- Per-key sliding-window rate limit (Redis), default 60 req/min, configurable
- Per-key usage counters (calls, touchpoints processed)
- Audit log table

**Exit:** Curl with valid key works; missing/bad key returns structured 401/403; exceeding limit returns 429 with `Retry-After`.

### M2 — Datasets API (Week 1-2, ~3 days)
**Goal:** Decouple upload from analysis. Datasets are first-class.

- `POST /v2/datasets` (multipart upload or signed URL flow) → returns `dataset_id`
- `GET /v2/datasets`, `GET /v2/datasets/{id}`, `DELETE /v2/datasets/{id}`
- Storage: local disk in dev, S3-compatible in prod (configurable)
- Background validation job → `dataset.status = ready|invalid` + validation report
- Touchpoint count + schema fingerprint stored

**Exit:** Upload a CSV, get back a dataset_id, poll until ready, fetch validation report.

### M3 — Async Analyses + Comparison (Week 2, ~4 days)
**Goal:** The core differentiator endpoint ships.

- `POST /v2/analyses` accepts `dataset_id` + `models[]` (one or many) → returns 202 + `analysis_id`
- Background worker (arq on Redis) runs requested models
- `GET /v2/analyses/{id}` returns status + results when ready
- Results include per-model channel attribution AND a `comparison` block (diff of credit by channel across models)
- Idempotency-Key header support on POST

**Exit:** One call, 5 models, structured comparison response. Documented in spec.

### M4 — Webhooks + SDK (Week 3, ~4 days)
**Goal:** Developers integrate without polling and without writing HTTP by hand.

- `POST /v2/webhooks` (subscribe to `analysis.completed`, `analysis.failed`, `dataset.validated`)
- HMAC-SHA256 signature header; retry with exponential backoff; delivery log
- Python SDK (`rabbit-sdk`) generated from OpenAPI with hand-tuned ergonomic layer
- SDK published to PyPI under a pre-release tag
- README quickstart: 8 lines of Python to first comparison result

**Exit:** A test marketing-tool integration runs end-to-end using only the SDK.

### M5 — Docs, Hosting, Launch (Week 3-4, ~3 days)
**Goal:** A developer who finds Rabbit can integrate in under 10 minutes.

- Hosted docs site (Mintlify or Docusaurus) with runnable examples
- Public OpenAPI spec at `/v2/openapi.json` + Postman collection in repo
- Hosted preview environment (Fly.io or Render) with rate-limited free tier
- Status page (Better Stack or hand-rolled)
- CHANGELOG.md with semver discipline starting v2.0.0
- Landing page section: "for developers building marketing tools"

**Exit:** Public GA. README has a curl example that works against the hosted URL.

---

## Out of scope for v2 GA (parked for v2.1+)

- JS/TS SDK (after Python lands and gets used)
- Billing / Stripe integration (manual key issuance until we have demand signal)
- Data connectors (Snowflake/BigQuery/S3 ingest)
- Scheduled re-runs
- Multi-region / SOC2
- Custom attribution models (user-defined weights)
- Frontend UI changes (the React app stays on v1 until v2 stabilizes; migrate in v2.1)

---

## Success metrics (90 days post-GA)

| Metric | Target |
|---|---|
| Self-serve sign-ups (key issued) | 50 |
| Activated (≥1 successful analysis) | 20 |
| Integrated (≥100 analyses via SDK) | 5 |
| GitHub stars | 100 |
| p95 analysis latency (10K touchpoints) | < 30s |
| API uptime | 99.5% |

---

## Risks & mitigations

| Risk | Mitigation |
|---|---|
| Scope creep into Path B features (SSO, connectors) | Roadmap is the source of truth; new ideas go to `Backlog.md` |
| Async job framework choice (arq vs Celery vs RQ) | Pick arq for simplicity; isolate behind a `JobQueue` interface so swap is cheap |
| OpenAPI → SDK generation produces ugly SDK | Hand-tune ergonomic layer over generated client; don't ship raw generated code |
| Hosted infra cost on free tier | Start on Fly.io with scale-to-zero; cap worker concurrency |
| v1 frontend breaks when backend versions split | Pin frontend to `/v1/*` until M5; migrate as separate effort |
