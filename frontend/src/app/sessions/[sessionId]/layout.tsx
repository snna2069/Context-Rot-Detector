import { getSession } from "@/lib/api/sessions";
import { orNotFound } from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { SessionTabs } from "@/components/SessionTabs";
import { RunAnalysisButton } from "@/components/RunAnalysisButton";
import { ClockIcon } from "@/components/icons";
import { formatDuration } from "@/lib/format";
import type { SessionStatus } from "@/lib/api/types";

const statusAccentClasses: Record<SessionStatus, string> = {
  active: "from-emerald-400 to-emerald-600",
  completed: "from-slate-300 to-slate-500",
  failed: "from-red-400 to-red-600",
  archived: "from-slate-200 to-slate-400",
};

export default async function SessionLayout({
  children,
  params,
}: LayoutProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const session = await orNotFound(getSession(sessionId));

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-6 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
        <div className={`h-1.5 w-full bg-gradient-to-r ${statusAccentClasses[session.status]}`} />
        <div className="flex flex-wrap items-start justify-between gap-4 p-5">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
                {session.name}
              </h1>
              <StatusBadge status={session.status} />
            </div>
            <p className="mt-1 font-mono text-xs text-slate-400">{session.id}</p>
            <p className="mt-2 inline-flex items-center gap-1.5 text-sm text-slate-600">
              <ClockIcon className="h-4 w-4 text-slate-400" />
              Duration: {formatDuration(session.started_at, session.ended_at)}
            </p>
          </div>
          <RunAnalysisButton sessionId={sessionId} />
        </div>
      </div>

      <SessionTabs sessionId={sessionId} />

      <div className="animate-fade-in pt-6">{children}</div>
    </main>
  );
}
