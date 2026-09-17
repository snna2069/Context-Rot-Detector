import { getSession } from "@/lib/api/sessions";
import { orNotFound } from "@/lib/api/client";
import { StatusBadge } from "@/components/StatusBadge";
import { SessionTabs } from "@/components/SessionTabs";
import { RunAnalysisButton } from "@/components/RunAnalysisButton";
import { formatDuration } from "@/lib/format";

export default async function SessionLayout({
  children,
  params,
}: LayoutProps<"/sessions/[sessionId]">) {
  const { sessionId } = await params;
  const session = await orNotFound(getSession(sessionId));

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
              {session.name}
            </h1>
            <StatusBadge status={session.status} />
          </div>
          <p className="mt-1 text-xs text-slate-400">{session.id}</p>
          <p className="mt-1 text-sm text-slate-600">
            Duration: {formatDuration(session.started_at, session.ended_at)}
          </p>
        </div>
        <RunAnalysisButton sessionId={sessionId} />
      </div>

      <SessionTabs sessionId={sessionId} />

      <div className="pt-6">{children}</div>
    </main>
  );
}
