import type { AnalysisRun } from "@/lib/api/types";

/** Makes the persisted analysis recipe visible without exposing prompts. */
export function AnalysisProvenance({ run }: { run: AnalysisRun | null }) {
  if (!run) return null;

  return (
    <section
      aria-labelledby="analysis-provenance-heading"
      className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h2
        id="analysis-provenance-heading"
        className="font-medium text-slate-900"
      >
        Analysis provenance
      </h2>
      <p className="mt-1 text-sm text-slate-600">
        These identifiers describe the detector and prompt configuration
        behind the persisted results. Session content is not duplicated here.
      </p>
      <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-400">
            Detector version
          </dt>
          <dd className="mt-1 break-words font-mono text-slate-700">
            {run.analysis_version}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-400">
            Prompt version
          </dt>
          <dd className="mt-1 break-words font-mono text-slate-700">
            {run.prompt_version}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-400">
            Provider / model
          </dt>
          <dd className="mt-1 break-words text-slate-700">
            {run.provider_name ?? "unknown"} / {run.model_name ?? "unknown"}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-400">
            LLM calls
          </dt>
          <dd className="mt-1 text-slate-700">{run.llm_call_count}</dd>
        </div>
      </dl>
    </section>
  );
}
