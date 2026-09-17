import type { DetectionSeverity } from "@/lib/api/types";
import { severityLabels } from "@/lib/format";

/** Dot + badge colors per severity, kept alongside (not replacing)
 * `severityColorClasses` in `lib/format`, which is reused for the filter
 * dropdown legend. */
const severityDotClasses: Record<DetectionSeverity, string> = {
  info: "bg-slate-400",
  low: "bg-blue-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

const severityBadgeClasses: Record<DetectionSeverity, string> = {
  info: "bg-slate-100 text-slate-700 ring-slate-300",
  low: "bg-blue-50 text-blue-700 ring-blue-200",
  medium: "bg-amber-50 text-amber-800 ring-amber-200",
  high: "bg-orange-50 text-orange-800 ring-orange-200",
  critical: "bg-red-50 text-red-800 ring-red-200",
};

export function SeverityBadge({ severity }: { severity: DetectionSeverity }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${severityBadgeClasses[severity]}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${severityDotClasses[severity]} ${severity === "critical" ? "animate-pulse" : ""}`}
      />
      {severityLabels[severity]}
    </span>
  );
}
