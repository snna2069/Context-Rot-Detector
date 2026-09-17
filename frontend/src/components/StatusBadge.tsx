import type { SessionStatus } from "@/lib/api/types";
import { sessionStatusLabels } from "@/lib/format";

const statusDotClasses: Record<SessionStatus, string> = {
  active: "bg-emerald-500 animate-pulse",
  completed: "bg-slate-400",
  failed: "bg-red-500",
  archived: "bg-slate-300",
};

const statusBadgeClasses: Record<SessionStatus, string> = {
  active: "bg-emerald-50 text-emerald-700 ring-emerald-200",
  completed: "bg-slate-100 text-slate-700 ring-slate-300",
  failed: "bg-red-50 text-red-800 ring-red-200",
  archived: "bg-slate-50 text-slate-500 ring-slate-200",
};

export function StatusBadge({ status }: { status: SessionStatus }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${statusBadgeClasses[status]}`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${statusDotClasses[status]}`} />
      {sessionStatusLabels[status]}
    </span>
  );
}
