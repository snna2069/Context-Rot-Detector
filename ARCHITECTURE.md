# Context Rot Detector Architecture

Status: Phase 0 audit and minimum architecture proposal  
Date: 2026-09-11

This document records the repository audit and the smallest architecture that can
support evidence-based context-rot detection. It is intentionally a design
document, not an implementation plan for the full product.

## 1. Repository audit

### 1.1 Directory structure

The repository currently contains two application directories:

```text
.
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py
│   ├── .gitignore
│   └── requirements.txt
└── frontend/
    ├── public/
    ├── src/app/
    │   ├── favicon.ico
    │   ├── globals.css
    │   ├── layout.tsx
    │   └── page.tsx
    ├── .gitignore
    ├── AGENTS.md
    ├── CLAUDE.md
    ├── eslint.config.mjs
    ├── next.config.ts
    ├── package.json
    ├── package-lock.json
    └── tsconfig.json
```

Local generated directories (`backend/.venv`, `frontend/node_modules`, and
`frontend/.next`) exist in the working directory but are not application source.

### 1.2 Frontend setup

The frontend is a default Next.js App Router application:

- Next.js `16.3.4`
- React `19.2.8`
- TypeScript `^5`
- Tailwind CSS `^4`
- ESLint 9 with `eslint-config-next`
- `src/app/page.tsx` is still the generated starter page.
- `src/app/layout.tsx` uses the generated Geist font setup and starter metadata.
- `src/app/globals.css` contains the default Tailwind and light/dark starter styles.
- `next.config.ts` has no custom configuration.
- No API client, domain types, state library, test runner, or product routes exist.

Existing scripts are `dev`, `build`, `start`, and `lint`.

### 1.3 Backend setup

The backend is a minimal FastAPI application:

- `app/main.py` creates a FastAPI application named `Context Rot Detector API`.
- `GET /health` returns `{"status": "ok"}`.
- `app/config.py` is empty.
- `app/database.py` is empty.
- There are no routers, domain services, repositories, Pydantic request/response
  schemas, ORM models, or migrations.

### 1.4 Database setup

PostgreSQL is named in the project requirements and `psycopg2-binary` and
SQLAlchemy are installed, but no database connection or schema is configured.
There are:

- no `DATABASE_URL` handling;
- no engine or session factory;
- no ORM models;
- no migration tool or migration directory;
- no seed data;
- no database tests.

PostgreSQL should remain the source of truth for durable session and analysis
data.

### 1.5 Dependencies

Backend dependencies in `backend/requirements.txt` include:

- FastAPI, Starlette, Uvicorn
- Pydantic and Pydantic Settings
- SQLAlchemy
- `psycopg2-binary`
- `python-dotenv`
- AnyIO and related runtime packages

Frontend dependencies are limited to Next.js, React, React DOM, TypeScript
types, Tailwind/PostCSS, and ESLint.

No LLM SDK, embedding library, vector database client, task queue, cache,
observability SDK, authentication library, or migration package is present.

### 1.6 Environment configuration

No environment files are committed. The backend and frontend `.gitignore`
files exclude local environment files and common secret names. There is no
environment template or settings schema yet.

The future configuration boundary should use environment variables for database
URLs, backend/frontend origins, and LLM credentials. Secrets must not be stored
in source, migrations, fixtures, or client-side code.

### 1.7 Tests

No backend or frontend tests exist. There is no test runner configuration.

### 1.8 Linting and formatting

Frontend ESLint is configured through `eslint.config.mjs`, and `npm run lint`
passes when run from `frontend`. TypeScript strict mode is enabled in
`tsconfig.json`.

There is no backend linter, formatter, type checker, or test command configured.
Those should be added only when backend code is introduced and the chosen tools
solve an actual maintenance requirement.

### 1.9 CI/CD

There is no `.github` directory, workflow, build pipeline, deployment manifest,
Dockerfile, or deployment configuration.

### 1.10 Existing API contracts

The only API contract is:

```http
GET /health
```

Response:

```json
{"status": "ok"}
```

There are no session, event, analysis, or dashboard API contracts.

### 1.11 Existing migrations

No migration system or migration files exist.

### 1.12 Existing agent or LLM code

No agent integration, LLM client, prompt, embedding, similarity, contradiction,
fact extraction, or hallucination detection code exists.

### 1.13 Existing deployment configuration

There is no deployment configuration. The intended target is a Vercel-hosted
frontend, an independently hosted FastAPI backend, and managed PostgreSQL, but
none of those environments are wired into the repository.

## 2. Minimum architecture

The first production-shaped architecture should be a modular monolith:

```text
Next.js frontend
        |
        | JSON over HTTPS
        v
FastAPI API layer
        |
        +--> domain services and analysis pipeline
        |
        +--> repositories
                  |
                  v
             PostgreSQL

Optional LLM provider is accessed only through an analysis interface.
```

This preserves a simple deployment model while keeping domain logic independent
from HTTP, SQLAlchemy, and any particular model provider.

### 2.1 Frontend

#### Pages and routes

Start with the following App Router routes:

- `/` - session list and high-level health summary.
- `/sessions/[sessionId]` - session timeline, health measurements, and detections.
- `/sessions/[sessionId]/events/[eventId]` - optional focused evidence view when
  the timeline cannot provide enough detail.

The event detail route should not be created until the timeline proves that a
separate page improves investigation; an expandable evidence panel may be
enough initially.

#### Dashboard structure

The session detail dashboard should contain:

1. Session header: identifier, task/status, event count, last activity.
2. Context health summary: measurements with timestamp and analysis version.
3. Event timeline: user messages, agent responses, instructions, tool calls,
   tool results, and snapshots with stable event IDs.
4. Detection panel: signal, classification, confidence, explanation, and links
   to source events.
5. Evidence state: verified, conflicting, unsupported, possible hallucination,
   high-confidence hallucination, or insufficient evidence.

The UI must not reduce uncertain evidence to a binary hallucination badge.

#### API client boundary

All browser-to-backend calls should go through a small typed client under
`frontend/src/lib/api/`. Components should consume typed functions rather than
constructing URLs or parsing untyped JSON themselves.

The client boundary should define:

- request/response types matching backend schemas;
- explicit handling for non-2xx responses;
- backend base URL from environment configuration;
- no secrets or provider credentials in browser code.

#### State management

Use React Server Components and route-level data loading by default. Use local
client state for filters, expanded evidence, and refresh controls. Do not add a
global state library until multiple pages demonstrate shared mutable state that
cannot be handled by URL state, server data, or small client components.

## 3. Backend architecture

### 3.1 API structure

Organize FastAPI routes by resource, not by implementation detail:

```text
backend/app/
├── api/
│   ├── health.py
│   ├── sessions.py
│   └── analysis.py
├── domain/
│   ├── sessions.py
│   ├── events.py
│   └── detections.py
├── schemas/
├── services/
│   ├── session_service.py
│   ├── analysis_service.py
│   └── llm/
├── repositories/
├── models/
├── config.py
├── database.py
└── main.py
```

Recommended initial endpoints:

- `GET /health`
- `POST /sessions`
- `GET /sessions`
- `GET /sessions/{session_id}`
- `POST /sessions/{session_id}/events`
- `GET /sessions/{session_id}/events`
- `POST /sessions/{session_id}/analysis-runs`
- `GET /sessions/{session_id}/detections`
- `GET /sessions/{session_id}/health`

The API layer validates and serializes data. It should not contain signal
algorithms, SQL query composition, or provider-specific LLM logic.

### 3.2 Domain and services

Domain services own behavior such as event ordering, evidence association,
analysis orchestration, and classification rules. Repositories own persistence
queries. Pydantic schemas define external contracts; domain types should not be
forced to mirror HTTP payloads when their invariants differ.

Analysis runs should be explicit records with an analysis version, input
boundary, started/completed timestamps, and failure state. This makes results
auditable and reproducible.

### 3.3 Analysis pipeline

The minimum pipeline is:

1. Load an immutable, ordered session event window.
2. Normalize event types and timestamps.
3. Build candidate facts, claims, instructions, and tool-result references.
4. Run deterministic signals.
5. Optionally invoke an LLM adapter for extraction or comparison.
6. Correlate signals with source events and evidence.
7. Persist detections and health measurements.
8. Return the analysis run and its results.

Each stage should expose typed input/output and include an analysis version.
The pipeline should be callable from an API service without requiring a queue.

### 3.4 Persistence layer

Use SQLAlchemy for database access, with repositories as the only layer that
knows persistence details. Use parameterized queries and database constraints
for identifiers, event order, and foreign keys.

Transactions should cover event append operations and analysis result writes.
Analysis failures should be recorded explicitly rather than returned as an
apparently healthy result.

## 4. Database design

### 4.1 Core entities

Minimum durable entities:

- `sessions`
  - session ID, title/task, status, created/updated timestamps, metadata.
- `session_events`
  - event ID, session ID, sequence number, event type, content/payload,
    event timestamp, source metadata, content hash.
- `context_snapshots`
  - snapshot ID, session ID, sequence boundary, snapshot payload, timestamp.
- `important_facts`
  - fact ID, session ID, normalized subject/predicate/value, status, confidence,
    source event reference, superseded-by reference.
- `analysis_runs`
  - run ID, session ID, analysis version, input boundary, status, timestamps,
    error metadata.
- `detections`
  - detection ID, analysis run ID, signal type, evidence classification,
    confidence, explanation, timestamp.
- `detection_evidence`
  - detection ID, event/fact/tool-result reference, relationship type, excerpt
    or structured evidence metadata.
- `health_measurements`
  - session ID, analysis run ID, measurement type, value, timestamp.

Raw event payloads should remain available for audit, but sensitive content
should not be copied into logs or redundant columns without a clear need.

### 4.2 Relationships

- One session has many events, snapshots, facts, analysis runs, detections, and
  health measurements.
- One analysis run produces many detections and health measurements.
- One detection has many evidence references.
- Facts reference the event(s) that support them and may reference a superseding
  fact.

### 4.3 Indexes and constraints

Initial indexes:

- `session_events(session_id, sequence_number)` for timeline reads.
- `session_events(session_id, event_timestamp)` for time-window reads.
- `session_events(session_id, content_hash)` for duplicate detection.
- `analysis_runs(session_id, created_at)` for run history.
- `detections(analysis_run_id, signal_type)` for dashboard filtering.
- `health_measurements(session_id, measured_at)` for trend charts.

Constraints should enforce:

- unique session event sequence numbers within a session;
- valid event and status values;
- foreign-key integrity;
- non-negative confidence in the `[0, 1]` range;
- immutable event identity and stable timestamps after ingestion.

### 4.4 Migration strategy

Introduce a migration tool when the first persistent schema is implemented.
Migrations must be versioned, reviewed, and applied before application startup
in deployed environments. Schema changes should be backward-compatible during
rolling deployments where the hosting platform requires it.

Do not rely on `metadata.create_all()` as the production schema management
mechanism.

## 5. AI and analysis layer

### 5.1 LLM abstraction

Define an internal provider-neutral interface, for example:

```text
analyze(request: AnalysisRequest) -> AnalysisResult
```

The request should include only the minimum evidence window and task needed for
the operation. The result must be validated against a typed schema containing
claims, evidence references, classifications, confidence, and explanation.

Provider adapters belong under `services/llm/`. The domain and API layers must
not import a provider SDK directly.

The adapter boundary must preserve model identifier, prompt/template version,
request scope, latency, token/cost metadata when available, and explicit
failure details.

### 5.2 Analysis interface

Use separate analysis capabilities rather than one opaque "detect rot" call:

- fact and claim extraction;
- contradiction comparison;
- instruction adherence comparison;
- tool-result usage comparison;
- relevance/repetition scoring;
- uncertainty assessment.

This allows deterministic signals to remain useful when an LLM is unavailable
and makes each result explainable.

### 5.3 Hallucination detection interface

Hallucination detection should be an evidence adjudication interface, not a
free-form label generator:

```text
classify_claim(
    claim,
    available_evidence,
    prior_facts,
    task_instructions
) -> EvidenceAssessment
```

`EvidenceAssessment` should support:

- `verified_fact`
- `conflicting_fact`
- `unsupported_claim`
- `possible_hallucination`
- `high_confidence_hallucination`
- `insufficient_evidence`

Every assessment must include the evidence references used, confidence,
explanation, and timestamp. A missing evidence reference must prevent a
high-confidence hallucination classification.

### 5.4 Deterministic signals

Begin with explainable signals:

- repeated event/content ratio;
- stale or superseded fact usage;
- explicit fact conflicts;
- instruction drift against recorded system/developer instructions;
- relevant tool result not reflected in a subsequent response;
- unsupported claims relative to the stored session evidence;
- unresolved contradiction count and evidence coverage.

Semantic similarity or embeddings should be introduced only after a measured
need for fuzzy relevance or duplicate detection. The initial design does not
require a vector database or a separate retrieval service.

### 5.5 Evidence model

Evidence is first-class data. A detection should point to source event IDs,
fact IDs, or tool-result IDs and identify how each source supports or conflicts
with the conclusion. Excerpts may be stored for display, but the original
event remains authoritative.

Confidence expresses analysis confidence, not truth in the external world.
The UI and API must preserve that distinction.

## 6. Phase 5 implementation: semantic/LLM analysis layer

This section documents what was actually built in Phase 5, as the
concrete realization of the abstraction described in section 5.

### 6.1 Where the code lives

- `app/services/llm/` -- the provider-neutral abstraction and its
  concrete implementations. `provider.py` defines the `AnalysisProvider`
  `Protocol` (six narrow methods, one per analysis task from section
  5.2). `types.py` defines every result dataclass and the
  `EvidenceClassification` enum. `unavailable.py` and `openai_provider.py`
  are the two concrete providers; `factory.py` picks between them based
  on `Settings.llm_api_key`. Nothing outside this package imports an LLM
  SDK or a provider-specific type.
- `app/analysis/semantic/` -- consumes `AnalysisProvider` to add semantic
  detectors and the hallucination-risk pipeline, parallel to (not
  replacing) `app/analysis/detectors/`.

### 6.2 Why `httpx` and not a vendor SDK

`httpx` was already a transitive dependency (via FastAPI's `TestClient`).
`OpenAIAnalysisProvider` calls a single `/chat/completions`-shaped HTTP
endpoint, so no additional SDK earns its keep -- the same code works
against OpenAI, Azure OpenAI-compatible endpoints, or a self-hosted
OpenAI-compatible server, by changing only `LLM_BASE_URL`.

### 6.3 Why an "Unavailable" provider instead of an `if llm_configured` branch

`UnavailableAnalysisProvider` is a Null Object, not fake AI: every method
returns an honest, zero-confidence result. Every semantic detector already
requires a minimum provider confidence before emitting a signal, so wiring
this provider in makes the semantic detectors run and safely emit nothing.
This means `app/services/analysis.py` never needs to ask "is a real LLM
configured?" -- the safety is structural (a confidence threshold), not a
conditional code path that could be forgotten or bypassed.

### 6.4 The hallucination-risk pipeline is not a single LLM call

`app/analysis/semantic/hallucination.py::assess_hallucination_risk` is the
concrete implementation of the pipeline in section 5.3. It is the *only*
place in the codebase that can produce a `POSSIBLE_HALLUCINATION` or
`HIGH_CONFIDENCE_HALLUCINATION` classification:

1. `provider.extract_important_facts(claim)` -- ask only "what claims does
   this contain?", never "is this true?".
2. `provider.assess_claim_support(fact, evidence)` -- ask only "does this
   evidence support/contradict/say nothing about this fact?", restricted
   at the type level (`ClaimSupportResult.__post_init__`) to the four
   evidence-only classifications. A provider cannot construct a result
   labelled as a hallucination-risk classification even if a model
   ignores its prompt and tries to.
3. A deterministic Python function (`_aggregate`) combines the per-fact
   results by priority (contradiction > unsupported > supported >
   insufficient) with fixed confidence rules -- **not** another LLM call
   -- into the final classification.

"No evidence provided" is treated as a *confident* `INSUFFICIENT_EVIDENCE`
result (confidence 1.0): certainty that nothing exists to check the claim
against, which is a different kind of confidence than "confidence the
claim itself is true or false" -- this pipeline never asserts the latter.

### 6.5 Semantic detectors reuse existing `DetectionType` values

`SemanticContradictionDetector`, `SemanticInstructionDriftDetector`,
`SemanticRelevanceDetector`, and `ClaimSupportDetector` all conform to the
same `Detector` protocol from Phase 4 (`app/analysis/base.py`) with zero
changes to it or to `AnalysisEngine`; only their constructors differ (they
take an `AnalysisProvider`). They emit the pre-existing `CONTRADICTION`,
`INSTRUCTION_DRIFT`, `TOPIC_DRIFT`, and `UNSUPPORTED_CLAIM` detection
types respectively -- no new enum members or migration were needed.
`UNSUPPORTED_CLAIM` was also added to health scoring's
`_EVIDENCE_COVERAGE_TYPES` set alongside the existing
`TOOL_RESULT_MISUSE`.

### 6.6 Known limitations (tracked as technical debt)

- All comparisons use small, bounded lookback/lookahead windows (a few
  messages) rather than exhaustive all-pairs comparison, to bound
  per-analysis-run LLM call volume and latency. Long-range relationships
  outside the window are missed.
- The aggregation thresholds in `hallucination.py` (e.g. the 0.75
  high-confidence-contradiction cutoff, the 0.7 possible-hallucination
  cap) are reasoned defaults, not calibrated against real-world labeled
  data.
- Provider/model identity is recorded in `Signal.metadata`, not a
  dedicated `DetectionEvent` column -- consistent with how detector
  metadata was already handled in Phase 4, but a real schema change if
  the UI ever needs to query/filter by it directly.
- `OpenAIAnalysisProvider` has no retry/backoff logic; a transient network
  failure surfaces as a skipped signal for that call, not a retried one.
- There is no live-API test coverage (by design, per the instruction that
  unit tests must not require a live LLM) -- `OpenAIAnalysisProvider`'s
  request/response handling is validated only against `httpx.MockTransport`.

## 7. Explicit non-goals for now

Do not build these in Phase 0 or the first vertical slice:

- microservices;
- Redis, Kafka, or another message broker;
- Kubernetes or a custom orchestration platform;
- a vector database or semantic search service;
- real-time WebSocket streaming;
- autonomous agent execution;
- automatic prompt rewriting or agent intervention;
- binary hallucination labels without evidence;
- external web fact verification;
- multi-provider LLM routing;
- fine-tuning or model training;
- organization billing and usage metering;
- complex role-based access control before the ownership model is defined;
- analytics warehouses or event-sourcing infrastructure;
- deployment automation before the local application contracts are stable.

These may become appropriate later, but each requires a concrete latency,
volume, compliance, or product requirement.

## 8. Decision summary

The minimum viable architecture is a typed Next.js client over a modular
FastAPI backend using PostgreSQL, with deterministic analysis first and an
optional provider-neutral LLM adapter later. The central design constraint is
evidence preservation: the system should explain why a signal was raised and
what remains uncertain, rather than claim that context length alone caused
degradation.
