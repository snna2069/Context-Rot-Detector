export default function DetectionEventNotFound() {
  return (
    <main className="mx-auto w-full max-w-3xl px-6 py-16 text-center">
      <h1 className="text-xl font-semibold text-slate-900">
        Detection event not found
      </h1>
      <p className="mt-2 text-sm text-slate-600">
        There is no detection event with this ID for this session.
      </p>
    </main>
  );
}
