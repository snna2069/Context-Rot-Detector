import type { ComponentType } from "react";
import type { ContextHealthScore } from "@/lib/api/types";
import { formatScorePercent } from "@/lib/format";
import {
  ActivityIcon,
  CheckCircleIcon,
  ChatBubbleIcon,
  ExclamationTriangleIcon,
  InboxIcon,
  WrenchIcon,
} from "@/components/icons";

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
  icon: ComponentType<{ className?: string }>;
  /** Whether a *lower* value is better for this dimension (risk-style
   * scores) rather than higher-is-better. Purely affects the bar color,
   * never the number shown. */
  inverse?: boolean;
}[] = [
  { key: "relevance_score", label: "Relevance", icon: ChatBubbleIcon },
  { key: "consistency_score", label: "Factual consistency", icon: CheckCircleIcon },
  { key: "instruction_adherence_score", label: "Instruction adherence", icon: ActivityIcon },
  { key: "information_retention_score", label: "Information retention", icon: InboxIcon },
  { key: "tool_utilization_score", label: "Tool-result utilization", icon: WrenchIcon },
  {
    key: "hallucination_risk_score",
    label: "Hallucination risk",
    icon: ExclamationTriangleIcon,
    inverse: true,
  },
];

function barColor(score: number | null, inverse?: boolean): string {
  if (score === null) return "bg-slate-200";
  const effective = inverse ? 1 - score : score;
  if (effective >= 0.75) return "bg-gradient-to-r from-emerald-400 to-emerald-500";
  if (effective >= 0.5) return "bg-gradient-to-r from-amber-400 to-amber-500";
  return "bg-gradient-to-r from-red-400 to-red-500";
}

function iconTone(score: number | null, inverse?: boolean): string {
  if (score === null) return "text-slate-400";
  const effective = inverse ? 1 - score : score;
  if (effective >= 0.75) return "text-emerald-500";
  if (effective >= 0.5) return "text-amber-500";
  return "text-red-500";
}

export function HealthDimensionBreakdown({
  score,
}: {
  score: ContextHealthScore;
}) {
  return (
    <div className="space-y-4">
      {DIMENSIONS.map((dimension) => {
        const value = score[dimension.key];
        const Icon = dimension.icon;
        return (
          <div key={dimension.key}>
            <div className="flex items-center justify-between text-xs text-slate-600">
              <span className="inline-flex items-center gap-1.5">
                <Icon className={`h-3.5 w-3.5 ${iconTone(value, dimension.inverse)}`} />
                {dimension.label}
              </span>
              <span className="font-semibold text-slate-800">
                {formatScorePercent(value)}
              </span>
            </div>
            <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-slate-100">
              <div
                className={`h-full rounded-full transition-all duration-500 ${barColor(value, dimension.inverse)}`}
                style={{ width: `${Math.round((value ?? 0) * 100)}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
