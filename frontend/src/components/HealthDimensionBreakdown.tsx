import type { ContextHealthScore } from "@/lib/api/types";
import { formatScorePercent } from "@/lib/format";

const DIMENSIONS: {
  key: keyof Pick<
    ContextHealthScore,
    | "relevance_score"
    | "consistency_score"
    | "instruction_adherence_score"
    | "information_retention_score"
    | "tool_utilization_score"
    | "hallucination_risk_score"
  >;
  label: string;
  /** Whether a *lower* value is better for this dimension (risk-style
   * scores) rather than higher-is-better. Purely affects the bar color,
   * never the number shown. */
  inverse?: boolean;
}[] = [
  { key: "relevance_score", label: "Relevance" },
  { key: "consistency_score", label: "Factual consistency" },
  { key: "instruction_adherence_score", label: "Instruction adherence" },
  { key: "information_retention_score", label: "Information retention" },
  { key: "tool_utilization_score", label: "Tool-result utilization" },
  { key: "hallucination_risk_score", label: "Hallucination risk", inverse: true },
];

function barColor(score: number | null, inverse?: boolean): string {
  if (score === null) return "bg-slate-200";
  const effective = inverse ? 1 - score : score;
  if (effective >= 0.75) return "bg-emerald-500";
  if (effective >= 0.5) return "bg-amber-500";
  return "bg-red-500";
}

export function HealthDimensionBreakdown({
  score,
}: {
  score: ContextHealthScore;
}) {
  return (
    <div className="space-y-3">
      {DIMENSIONS.map((dimension) => {
        const value = score[dimension.key];
        return (
          <div key={dimension.key}>
            <div className="flex justify-between text-xs text-slate-600">
              <span>{dimension.label}</span>
              <span className="font-medium text-slate-800">
                {formatScorePercent(value)}
              </span>
            </div>
            <div className="mt-1 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full ${barColor(value, dimension.inverse)}`}
                style={{ width: `${Math.round((value ?? 0) * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
