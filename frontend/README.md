# Context Rot Detector -- frontend

Next.js (App Router) + React + TypeScript + Tailwind dashboard for the
Context Rot Detector backend. For overall project context, setup from the
repository root, and architectural decisions, see the top-level
[`README.md`](../README.md) and [`ARCHITECTURE.md`](../ARCHITECTURE.md).

## Development

```powershell
npm ci
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app expects the
backend to be running (see the root README) and reads its base URL from
`NEXT_PUBLIC_API_BASE_URL` (see `.env.example`).

The frontend does not contain the backend API key. For an internal
deployment, put the same value in the server-only `API_KEY` environment
variable. Next.js uses it for server-rendered reads and the server-side
analysis proxy; it is never exposed through `NEXT_PUBLIC_*` browser
configuration.

## Structure

- `src/app/` -- routes: sessions list (`/`), and per-session timeline,
  context health, detection events, and hallucination analysis pages under
  `sessions/[sessionId]/`.
- `src/lib/api/` -- the only layer that knows backend endpoint paths and
  response shapes (typed client + types mirroring the backend Pydantic
  schemas field-for-field). `client.ts` applies a request timeout to every
  call; `validate.ts` checks the response fields the UI branches on, so a
  backend shape change fails at the boundary with a clear error rather
  than deep inside a component.
- `src/lib/format/` -- pure, unit-tested formatting/presentation helpers
  (severity/score labels, timestamp/duration formatting, sorting). No JSX,
  no fetching.
- `src/components/` -- presentational components (badges, cards, charts,
  the shared inline SVG icon set in `icons.tsx`) that take already-typed
  domain data as props. `AnalysisIntegrityNotice.tsx` warns when results
  came from an incomplete analysis run or are out of date, so absent
  detections are never read as a clean result.

## Checks

```powershell
npm run lint
npm run build
npm test
```

`npm test` runs the Vitest suite for `src/lib/format` and `src/lib/api`.
It also covers the API boundary validators, session-tab accessibility
state, and detection-event filter controls.
