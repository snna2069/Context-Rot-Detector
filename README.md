# Context Rot Detector

Context Rot Detector monitors long-running AI-agent sessions and surfaces
evidence-backed context degradation signals: contradictions, instruction
drift, stale context, information loss, tool-result neglect, and
hallucination risk. Every detection carries a confidence score, supporting
evidence, and an explanation -- the system never reports a suspicious signal
as an unqualified fact.

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

`npm test` runs the Vitest suite for the pure formatting/presentation helpers
in `src/lib/format`.

Backend:

```powershell
Set-Location backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pytest
```

The backend suite covers domain models, migrations, ingestion, every
deterministic detector, the semantic analysis pipeline (mocked provider,
no live LLM calls), and health scoring.

There is no CI/CD configured yet -- run these checks locally before
committing.

## Environment variables

See `.env.example` for backend settings and `frontend/.env.example` for the
browser-visible API base URL. Do not commit `.env`, `.env.local`, or secrets.
