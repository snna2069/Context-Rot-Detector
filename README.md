# Context Rot Detector

Context Rot Detector is being built to monitor long-running AI-agent sessions
and surface evidence-backed context degradation signals. The repository is
currently at the Phase 1 foundation: application wiring is present, but session
ingestion and analysis are intentionally not implemented yet.

## Repository layout

- `frontend/` - Next.js, React, TypeScript, and Tailwind frontend.
- `backend/` - FastAPI, Pydantic, SQLAlchemy, and PostgreSQL integration.
- `backend/migrations/` - Alembic migrations.
- `ARCHITECTURE.md` - audit and architectural decisions.

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

Open `http://localhost:3000`. The page checks the backend through the typed API
client at `http://localhost:8000/health`.

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
```

Backend:

```powershell
Set-Location backend
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe -m pytest
```

## Environment variables

See `.env.example` for backend settings and `frontend/.env.example` for the
browser-visible API base URL. Do not commit `.env`, `.env.local`, or secrets.
