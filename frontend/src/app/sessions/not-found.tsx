/**
 * Renders when the `[sessionId]` layout's own existence check (`getSession`)
 * fails with a 404. This file must live in the *parent* segment (`sessions/`)
 * rather than alongside the layout: a `notFound()` thrown inside
 * `[sessionId]/layout.tsx` cannot be caught by that same segment's
 * `not-found.tsx`, because the layout wraps everything in its own segment,
 * including that file. Next.js instead resolves to the nearest ancestor
 * segment's `not-found.tsx`, which is this one.
 */
export default function SessionNotFound() {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-16 text-center">
      <h1 className="text-xl font-semibold text-slate-900">
        Session not found
      </h1>
      <p className="mt-2 text-sm text-slate-600">
        There is no session with this ID. It may have been removed, or the
        link may be incorrect.
      </p>
    </main>
  );
}
