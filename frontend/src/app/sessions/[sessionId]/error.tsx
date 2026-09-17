"use client";

export default function SessionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="rounded-lg border border-red-200 bg-red-50 px-6 py-8 text-center">
        <p className="text-sm font-medium text-red-800">
          Could not load this session
        </p>
        <p className="mt-1 text-sm text-red-700">{error.message}</p>
        <button
          onClick={reset}
          className="mt-4 rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-800 hover:bg-red-50"
        >
          Try again
        </button>
      </div>
    </main>
  );
}
