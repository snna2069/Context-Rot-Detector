"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { analyzeSession } from "@/lib/api/analysis";
import { ApiError } from "@/lib/api/client";
import { BoltIcon, SpinnerIcon } from "@/components/icons";

export function RunAnalysisButton({ sessionId }: { sessionId: string }) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  const handleClick = () => {
    setError(null);
    startTransition(async () => {
      try {
        await analyzeSession(sessionId);
        router.refresh();
      } catch (cause) {
        setError(
          cause instanceof ApiError
            ? cause.message
            : "Analysis failed unexpectedly.",
        );
      }
    });
  };

  return (
    <div className="flex flex-col items-end gap-1">
      <button
        onClick={handleClick}
        disabled={isPending}
        className="inline-flex items-center gap-1.5 rounded-lg bg-gradient-to-br from-slate-900 to-slate-700 px-3.5 py-2 text-sm font-medium text-white shadow-sm transition hover:from-slate-800 hover:to-slate-600 hover:shadow disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? (
          <SpinnerIcon className="h-4 w-4" />
        ) : (
          <BoltIcon className="h-4 w-4" />
        )}
        {isPending ? "Running analysis…" : "Run analysis"}
      </button>
      {error ? <p className="max-w-xs text-right text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
