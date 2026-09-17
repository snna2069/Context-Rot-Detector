import { getHealthTrend, listHealthScores } from "@/lib/api/analysis";
import { orNotFound } from "@/lib/api/client";
import { EmptyState } from "@/components/EmptyState";
import { HealthTrendChart } from "@/components/HealthTrendChart";
import { HealthDimensionBreakdown } from "@/components/HealthDimensionBreakdown";
import { ScoreBadge } from "@/components/ScoreBadge";
import { ActivityIcon } from "@/components/icons";
import { formatScorePercent, formatTimestamp } from "@/lib/format";

const trendDirectionLabels: Record<string, string> = {
  improving: "Improving",
  stable: "Stable",
  degrading: "Degrading",
};

const trendDirectionClasses: Record<string, string> = {
  improving: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  stable: "bg-slate-100 text-slate-600 ring-slate-300",
  degrading: "bg-red-50 text-red-700 ring-red-200",
};

export default async function SessionHealthPage({
  params,
}: PageProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const [scores, trend] = await Promise.all([
    orNotFound(listHealthScores(sessionId)),
    orNotFound(getHealthTrend(sessionId)),
  ]);

  if (scores.length === 0) {
    return (
      <EmptyState
        title="No health scores yet"
        description={'Run analysis on this session ("Run analysis" above) to compute a context health score.'}
      />
    );
  }

  const latest = scores[scores.length - 1];

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="inline-flex items-center gap-2 font-medium text-slate-900">
            <ActivityIcon className="h-4 w-4 text-indigo-500" />
            Health over time
          </h2>
          <span
            className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${trendDirectionClasses[trend.direction] ?? "bg-slate-100 text-slate-600 ring-slate-300"}`}
          >
            {trendDirectionLabels[trend.direction] ?? trend.direction}
          </span>
        </div>
        <p className="mt-2 text-sm text-slate-600">{trend.summary}</p>
        <p className="mt-1 text-xs text-slate-400">
          This trend is a simple linear estimate over recorded checkpoints,
          not a statistically validated forecast.
        </p>
        <div className="mt-4">
          <HealthTrendChart points={trend.points} />
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="font-medium text-slate-900">
              Latest checkpoint
            </h2>
            <ScoreBadge score={latest.overall_score} />
          </div>
          <p className="mt-1 text-xs text-slate-400">
            Measured {formatTimestamp(latest.measured_at)}
          </p>
          <div className="mt-4">
            <HealthDimensionBreakdown score={latest} />
          </div>
        </div>

        <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="font-medium text-slate-900">
            Why did the score change?
          </h2>
          <p className="mt-1 text-sm text-slate-600">
            {trend.explanation.headline}
          </p>
          {trend.explanation.score_delta !== null ? (
            <p
              className={`mt-2 inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium ${
                trend.explanation.score_delta < 0
                  ? "bg-red-50 text-red-700"
                  : trend.explanation.score_delta > 0
                    ? "bg-emerald-50 text-emerald-700"
                    : "bg-slate-100 text-slate-600"
              }`}
            >
              {trend.explanation.score_delta >= 0 ? "▲" : "▼"}{" "}
              {formatScorePercent(Math.abs(trend.explanation.score_delta))} since
              previous checkpoint
            </p>
          ) : null}
          {trend.explanation.reasons.length > 0 ? (
            <ul className="mt-4 space-y-2 text-sm text-slate-700">
              {trend.explanation.reasons.map((reason) => (
                <li key={reason} className="flex gap-2">
                  <span className="mt-1.5 h-1.5 w-1.5 flex-none rounded-full bg-red-400" />
                  {reason}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-4 text-sm text-slate-400">
              No specific contributing signal categories increased since the
              previous checkpoint.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
