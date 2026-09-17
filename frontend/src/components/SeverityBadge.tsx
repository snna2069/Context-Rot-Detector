import type { DetectionSeverity } from "@/lib/api/types";
import { severityColorClasses, severityLabels } from "@/lib/format";

export function SeverityBadge({ severity }: { severity: DetectionSeverity }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${severityColorClasses[severity]}`}
    >
      {severityLabels[severity]}
    </span>
  );
}
