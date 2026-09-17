import type {
  DetectionSeverity,
  HallucinationClassification,
  SessionStatus,
} from "@/lib/api/types";

/** Renders an ISO timestamp as an absolute, locale-formatted string. */
export function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "medium",
  });
}

/** Renders the duration between two ISO timestamps (or "now") as `1h 12m`. */
export function formatDuration(startIso: string, endIso: string | null): string {
  const start = new Date(startIso).getTime();
  const end = endIso ? new Date(endIso).getTime() : Date.now();
  const totalSeconds = Math.max(0, Math.round((end - start) / 1000));

  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${seconds}s`;
  return `${seconds}s`;
}

/** Renders a 0-1 score as a percentage string, e.g. `0.734` -> `73%`. */
export function formatScorePercent(score: number | null | undefined): string {
  if (score === null || score === undefined) return "—";
  return `${Math.round(score * 100)}%`;
}

export const sessionStatusLabels: Record<SessionStatus, string> = {
  active: "Active",
  completed: "Completed",
  failed: "Failed",
  archived: "Archived",
};

export const severityLabels: Record<DetectionSeverity, string> = {
  info: "Info",
  low: "Low",
  medium: "Medium",
  high: "High",
  critical: "Critical",
};

/** Tailwind color classes for severity badges, ordered from least to most
 * urgent. Kept as a single lookup table so severity -> color is defined
 * exactly once. */
export const severityColorClasses: Record<DetectionSeverity, string> = {
  info: "bg-slate-100 text-slate-700 border-slate-300",
  low: "bg-blue-50 text-blue-700 border-blue-300",
  medium: "bg-amber-50 text-amber-800 border-amber-300",
  high: "bg-orange-50 text-orange-800 border-orange-300",
  critical: "bg-red-50 text-red-800 border-red-300",
};

const severityOrder: Record<DetectionSeverity, number> = {
  info: 0,
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

export function compareSeverityDesc(
  a: DetectionSeverity,
  b: DetectionSeverity,
): number {
  return severityOrder[b] - severityOrder[a];
}

export const hallucinationClassificationLabels: Record<
  HallucinationClassification,
  string
> = {
  supported: "Supported",
  contradicted: "Contradicted",
  unsupported: "Unsupported claim",
  possible_hallucination: "Possible hallucination",
  high_confidence_hallucination: "High-confidence hallucination",
  insufficient_evidence: "Insufficient evidence",
};

/** Ordering used when grouping the hallucination-analysis view, from most
 * to least concerning. Only these four are ever emitted as detection
 * events in practice (see `ClaimSupportDetector._EMIT_CLASSIFICATIONS`
 * on the backend), but all six are covered for completeness. */
const classificationSeverityOrder: Record<HallucinationClassification, number> = {
  high_confidence_hallucination: 0,
  contradicted: 1,
  possible_hallucination: 2,
  unsupported: 3,
  insufficient_evidence: 4,
  supported: 5,
};

export function compareClassificationSeverity(
  a: HallucinationClassification,
  b: HallucinationClassification,
): number {
  return classificationSeverityOrder[a] - classificationSeverityOrder[b];
}

export function isHallucinationClassification(
  value: unknown,
): value is HallucinationClassification {
  return (
    typeof value === "string" &&
    value in hallucinationClassificationLabels
  );
}
