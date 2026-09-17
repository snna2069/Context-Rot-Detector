"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { analyzeSession } from "@/lib/api/analysis";
import { ApiError } from "@/lib/api/client";

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
        className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isPending ? "Running analysis…" : "Run analysis"}
      </button>
      {error ? <p className="max-w-xs text-right text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
