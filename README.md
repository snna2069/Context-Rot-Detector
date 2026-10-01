# Context Rot Detector

Context Rot Detector monitors long-running AI-agent sessions and surfaces
evidence-backed context degradation signals: contradictions, instruction
drift, stale context, information loss, tool-result neglect, and
hallucination risk. Every detection carries a confidence score, supporting
evidence, and an explanation -- the system never reports a suspicious signal
as an unqualified fact.

Equally, it never reports an *unmeasured* signal as a clean one. If a
detector fails (for example a semantic detector whose LLM call times out),
the analysis run is recorded as `partial` or `failed`, the health
dimensions that detector covered are reported as "not assessed" rather
than scored, and the dashboard says so. An absent detection from a failed
detector is not evidence that the condition is absent.

Phases 0-7 are implemented and validated:

- **Ingestion** -- provider-agnostic APIs for creating sessions and recording
  messages, tool calls, and tool results with validated ordering.
- **Deterministic detectors** -- composable, independently-testable signals
  for context growth, repetition, omission, instruction drift, contradiction,
  staleness, tool-result neglect, topic drift, behavior shifts, and fact loss.
- **Semantic/LLM analysis** -- an evidence-based pipeline (claim -> evidence
  -> comparison -> confidence -> classification) behind a swappable
  `AnalysisProvider` interface; unit tests use deterministic fixtures, no live
  LLM API is required.
- **Context health scoring** -- a transparent, configurably-weighted score
  across six dimensions, tracked over time with plain-language explanations
  of why it changed.
- **Dashboard** -- a Next.js UI over real backend data: sessions list, session
  timeline, health trend, detection events, and hallucination analysis, all
  with loading/empty/error states and no hard-coded production data.

See `ARCHITECTURE.md` for the full audit, data model, and the reasoning
behind every architectural decision (including what was deliberately not
built yet).

## Repository layout

- `frontend/` - Next.js (App Router), React, TypeScript, and Tailwind
  dashboard. See `frontend/README.md` for frontend-specific notes.
- `backend/` - FastAPI, Pydantic, SQLAlchemy, and PostgreSQL integration:
  domain models, ingestion API, detectors, analysis pipeline, and health
  scoring.
- `backend/migrations/` - Alembic migrations (schema is the source of truth
  for persistent data; nothing is stored as an opaque blob where querying
  matters).
- `ARCHITECTURE.md` - repository audit and architectural decisions, updated
  after every phase.

## Prerequisites

- Node.js 20 or newer
- Python 3.13 or newer
- PostgreSQL 14 or newer

## Local setup

From the repository root:

1. Create local environment files:

   ```powershell
   Copy-Item .env.example backend\.env
   Copy-Item frontend\.env.example frontend\.env.local
   ```

2. Create or select a PostgreSQL database named `context_rot`, then update
   `DATABASE_URL` in `backend\.env` if needed.

3. Install backend dependencies:

   ```powershell
   Set-Location backend
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   ```

4. Start the backend:

   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
   ```

5. In another terminal, install and start the frontend:

   ```powershell
   Set-Location frontend
   npm ci
   npm run dev
   ```

Open `http://localhost:3000`. The sessions list will be empty until you apply
migrations and load the seed data (below).

## Using the dashboard

Once seeded, `http://localhost:3000` shows the sessions list. Open a session
to see its timeline, then use the tab navigation to switch between context
health, detection events, and hallucination analysis. The "Run analysis"
button triggers a new `AnalysisRun` against the backend for that session.

## Database migrations

The Phase 2 domain migration creates the session, message,
tool, snapshot, fact, detection, health, and analysis tables:

```powershell
Set-Location backend
.\.venv\Scripts\alembic.exe upgrade head
```

To load the small realistic development dataset after applying migrations:

```powershell
.\.venv\Scripts\python.exe -m app.seed
```

## Checks

Frontend:

```powershell
Set-Location frontend
npm run lint
npm run build
npm test
```

`npm test` runs the Vitest suite for the pure formatting/presentation
helpers in `src/lib/format` and for the API client and response
validators in `src/lib/api`.

Backend:

```powershell
Set-Location backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pytest
```

The backend suite covers domain models, ingestion (including
concurrency-conflict handling), every deterministic detector, the
semantic analysis pipeline (mocked provider, no live LLM calls), health
scoring, and analysis-failure handling.

### Running the tests against PostgreSQL

By default the suite runs on in-memory SQLite with the schema built by
`Base.metadata.create_all()`, so it needs no database and never executes
a migration. Set `TEST_DATABASE_URL` to run the **same** suite against a
real PostgreSQL database whose schema is built by applying the Alembic
migrations, which additionally enables the migration tests (including the
model/migration drift check):

```powershell
docker run -d --name crd-test-pg `
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_USER=postgres `
  -e POSTGRES_DB=context_rot_test -p 55432:5432 postgres:16-alpine

$env:TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:55432/context_rot_test"
.\.venv\Scripts\python.exe -m pytest
```

Tear the container down with `docker rm -f crd-test-pg`. Anything not
covered by a PostgreSQL run -- JSON column behaviour, constraint
enforcement, transactional DDL -- is only exercised in this mode, so run
it before changing models or migrations.

### Detection-quality evaluation

The test suite answers "does the code behave as written?". A separate
harness answers "do the detectors actually identify context rot, and is
their confidence meaningful?":

```powershell
Set-Location backend
.\.venv\Scripts\python.exe -m evaluation          # human-readable report
.\.venv\Scripts\python.exe -m evaluation --json   # machine-readable
```

It runs the deterministic detectors over a labeled corpus of agent
sessions in `backend/evaluation/corpus/` and reports per-detector
precision, recall, false-positive rate and a confidence-calibration
curve. No LLM is called, so a run is free, offline and reproducible.

The corpus is small, author-written and single-labeled, so the numbers
are a **regression baseline, not a measure of real-world accuracy**. The
measured baseline is recorded in `backend/evaluation/baseline.json`, and
`tests/test_evaluation_harness.py` fails if quality drops below it. Read
`backend/evaluation/corpus/README.md` before adding scenarios -- labels
must come from the scenario's intent, never from what the detectors
happen to output.

CI also runs these checks; run them locally before committing for faster
feedback.

### Docker Compose

The repository includes a minimal single-service deployment shape with
PostgreSQL, the FastAPI backend, and the Next.js frontend:

```powershell
docker compose up --build
```

The backend applies Alembic migrations before starting. Open
`http://localhost:3000`; the API is available at `http://localhost:8000`.
The compose setup is intended for local/internal deployment, not as a
complete production orchestration or secret-management solution.

### CI

`.github/workflows/ci.yml` runs backend linting, the full backend suite
against a migration-built PostgreSQL service, the detection-quality
baseline, frontend lint/tests/build, and both container builds. The
PostgreSQL job is important: SQLite remains useful for fast local tests,
but CI also exercises the production database engine and the real
migration chain.

### Analysis provenance

Every `AnalysisRun` records `analysis_version`, `prompt_version`,
`provider_name`, `model_name`, and `llm_call_count`. This identifies which
detector/prompt/provider configuration produced persisted results without
persisting raw prompt text or duplicating session content. The prompt
version is currently `semantic-prompts-v2`.

### Internal-service security

The API is designed for an internal single-service deployment in this
phase. Set `API_KEY` in `backend/.env`; non-development environments
require it and reject missing or incorrect `X-API-Key` headers with 401.
When `AUTH_ENABLED` is omitted, development remains convenient without a
key, while all other environments fail closed. Do not put the key in the
frontend or in `NEXT_PUBLIC_*` configuration.

`POST /sessions/{session_id}/analyze` is also protected by an in-process
per-client rate limit (`ANALYSIS_RATE_LIMIT_PER_MINUTE`) and the LLM
provider has bounded retries plus a per-analysis call budget. These are
single-process safeguards, not a substitute for a gateway-level limit
when running multiple replicas.

## Environment variables

See `.env.example` for backend settings and `frontend/.env.example` for the
browser-visible API base URL. Do not commit `.env`, `.env.local`, or secrets.
