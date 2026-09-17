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

## Structure

- `src/app/` -- routes: sessions list (`/`), and per-session timeline,
  context health, detection events, and hallucination analysis pages under
  `sessions/[sessionId]/`.
- `src/lib/api/` -- the only layer that knows backend endpoint paths and
  response shapes (typed client + types mirroring the backend Pydantic
  schemas field-for-field).
- `src/lib/format/` -- pure, unit-tested formatting/presentation helpers
  (severity/score labels, timestamp/duration formatting, sorting). No JSX,
  no fetching.
- `src/components/` -- presentational components (badges, cards, charts,
  the shared inline SVG icon set in `icons.tsx`) that take already-typed
  domain data as props.

## Checks

```powershell
npm run lint
npm run build
npm test
```

`npm test` runs the Vitest suite for `src/lib/format`.
