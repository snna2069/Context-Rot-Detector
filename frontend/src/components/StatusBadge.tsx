import type { SessionStatus } from "@/lib/api/types";
import { sessionStatusLabels } from "@/lib/format";

const statusColorClasses: Record<SessionStatus, string> = {
  active: "bg-emerald-50 text-emerald-700 border-emerald-300",
  completed: "bg-slate-100 text-slate-700 border-slate-300",
  failed: "bg-red-50 text-red-800 border-red-300",
  archived: "bg-slate-50 text-slate-500 border-slate-200",
};

export function StatusBadge({ status }: { status: SessionStatus }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${statusColorClasses[status]}`}
    >
      {sessionStatusLabels[status]}
    </span>
  );
}
