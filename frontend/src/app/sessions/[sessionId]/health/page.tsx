import { getHealthTrend, listHealthScores } from "@/lib/api/analysis";
import { orNotFound } from "@/lib/api/client";
import { EmptyState } from "@/components/EmptyState";
import { HealthTrendChart } from "@/components/HealthTrendChart";
import { HealthDimensionBreakdown } from "@/components/HealthDimensionBreakdown";
import { ScoreBadge } from "@/components/ScoreBadge";
import { formatScorePercent, formatTimestamp } from "@/lib/format";

const trendDirectionLabels: Record<string, string> = {
  improving: "Improving",
  stable: "Stable",
  degrading: "Degrading",
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
        <div className="flex items-center justify-between">
          <h2 className="font-medium text-slate-900">Health over time</h2>
          <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
            {trendDirectionLabels[trend.direction] ?? trend.direction}
          </span>
        </div>
        <p className="mt-1 text-sm text-slate-600">{trend.summary}</p>
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
            <p className="mt-1 text-xs text-slate-400">
              Change since previous checkpoint:{" "}
              {trend.explanation.score_delta >= 0 ? "+" : ""}
              {formatScorePercent(Math.abs(trend.explanation.score_delta))}
              {trend.explanation.score_delta < 0 ? " decrease" : trend.explanation.score_delta > 0 ? " increase" : ""}
            </p>
          ) : null}
          {trend.explanation.reasons.length > 0 ? (
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-slate-700">
              {trend.explanation.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
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
