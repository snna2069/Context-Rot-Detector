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
