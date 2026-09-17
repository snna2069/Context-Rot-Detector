"use client";

import { useMemo, useState } from "react";
import type { DetectionEvent, DetectionSeverity } from "@/lib/api/types";
import { DetectionEventCard, detectionTypeLabel } from "@/components/DetectionEventCard";
import { EmptyState } from "@/components/EmptyState";
import { compareSeverityDesc } from "@/lib/format";

const SEVERITIES: DetectionSeverity[] = ["critical", "high", "medium", "low", "info"];

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
      <div className="flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700"
        >
          <option value="all">All detection types</option>
          {types.map((type) => (
            <option key={type} value={type}>
              {detectionTypeLabel(type)}
            </option>
          ))}
        </select>
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm text-slate-700"
        >
          <option value="all">All severities</option>
          {SEVERITIES.map((severity) => (
            <option key={severity} value={severity}>
              {severity}
            </option>
          ))}
        </select>
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
