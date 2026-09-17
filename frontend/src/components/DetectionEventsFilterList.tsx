"use client";

import { useMemo, useState } from "react";
import type { DetectionEvent, DetectionSeverity } from "@/lib/api/types";
import { DetectionEventCard, detectionTypeLabel } from "@/components/DetectionEventCard";
import { EmptyState } from "@/components/EmptyState";
import { compareSeverityDesc, severityLabels } from "@/lib/format";

const SEVERITIES: DetectionSeverity[] = ["critical", "high", "medium", "low", "info"];

const severityPillDot: Record<DetectionSeverity, string> = {
  info: "bg-slate-400",
  low: "bg-blue-500",
  medium: "bg-amber-500",
  high: "bg-orange-500",
  critical: "bg-red-500",
};

export function DetectionEventsFilterList({
  sessionId,
  events,
}: {
  sessionId: string;
  events: DetectionEvent[];
}) {
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");

  const types = useMemo(
    () => Array.from(new Set(events.map((e) => e.detection_type))).sort(),
    [events],
  );

  const filtered = useMemo(() => {
    return events
      .filter((e) => typeFilter === "all" || e.detection_type === typeFilter)
      .filter((e) => severityFilter === "all" || e.severity === severityFilter)
      .sort((a, b) => compareSeverityDesc(a.severity, b.severity));
  }, [events, typeFilter, severityFilter]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => setSeverityFilter("all")}
            className={`rounded-full px-3 py-1 text-xs font-medium transition ${
              severityFilter === "all"
                ? "bg-slate-900 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            }`}
          >
            All severities
          </button>
          {SEVERITIES.map((severity) => (
            <button
              key={severity}
              onClick={() => setSeverityFilter(severity)}
              className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition ${
                severityFilter === severity
                  ? "bg-slate-900 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${severityPillDot[severity]}`} />
              {severityLabels[severity]}
            </button>
          ))}
        </div>
        <div className="ml-auto">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700 focus:border-indigo-400 focus:outline-none focus:ring-1 focus:ring-indigo-400"
          >
            <option value="all">All detection types</option>
            {types.map((type) => (
              <option key={type} value={type}>
                {detectionTypeLabel(type)}
              </option>
            ))}
          </select>
        </div>
      </div>

      {filtered.length === 0 ? (
        <EmptyState
          title="No matching detection events"
          description="Try a different filter, or clear filters to see everything."
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((event) => (
            <DetectionEventCard key={event.id} sessionId={sessionId} event={event} />
          ))}
        </div>
      )}
    </div>
  );
}
