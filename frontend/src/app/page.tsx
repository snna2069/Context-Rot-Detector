import Link from "next/link";
import type { ComponentType } from "react";
import { listSessionOverviews } from "@/lib/api/sessions";
import { StatusBadge } from "@/components/StatusBadge";
import { ScoreBadge } from "@/components/ScoreBadge";
import { EmptyState } from "@/components/EmptyState";
import { ActivityIcon, ChevronRightIcon, ListIcon, ShieldIcon } from "@/components/icons";
import { formatDuration, formatScorePercent } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function SessionsListPage() {
  const overviews = await listSessionOverviews({ limit: 100 });

  const activeCount = overviews.filter((o) => o.session.status === "active").length;
  const scoredOverviews = overviews.filter((o) => o.latest_health_score);
  const avgHealth =
    scoredOverviews.length > 0
      ? scoredOverviews.reduce(
          (sum, o) => sum + (o.latest_health_score?.overall_score ?? 0),
          0,
        ) / scoredOverviews.length
      : null;
  const totalDetections = overviews.reduce((sum, o) => sum + o.detection_event_count, 0);

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
            Sessions
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Long-running agent sessions currently tracked by the detector.
          </p>
        </div>
      </div>

      {overviews.length > 0 ? (
        <div className="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <SummaryStat label="Sessions" value={String(overviews.length)} icon={ListIcon} accent="text-slate-500" />
          <SummaryStat label="Active now" value={String(activeCount)} icon={ActivityIcon} accent="text-emerald-500" />
          <SummaryStat
            label="Avg. context health"
            value={avgHealth === null ? "—" : formatScorePercent(avgHealth)}
            icon={ActivityIcon}
            accent="text-indigo-500"
          />
          <SummaryStat label="Detections logged" value={String(totalDetections)} icon={ShieldIcon} accent="text-amber-500" />
        </div>
      ) : null}

      {overviews.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          description="Ingest a session through the API to see it appear here."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Session</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Messages</th>
                <th className="px-4 py-3 font-medium">Context health</th>
                <th className="px-4 py-3 font-medium">Hallucination risk</th>
                <th className="px-4 py-3 font-medium">Detections</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {overviews.map((overview) => (
                <tr
                  key={overview.session.id}
                  className="group transition-colors hover:bg-indigo-50/40"
                >
                  <td className="px-4 py-3">
                    <Link
                      href={`/sessions/${overview.session.id}`}
                      className="font-medium text-slate-900 group-hover:text-indigo-700"
                    >
                      {overview.session.name}
                    </Link>
                    <div className="text-xs text-slate-400">
                      {overview.session.id}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={overview.session.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatDuration(
                      overview.session.started_at,
                      overview.session.ended_at,
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {overview.message_count}
                  </td>
                  <td className="px-4 py-3">
                    {overview.latest_health_score ? (
                      <ScoreBadge
                        score={overview.latest_health_score.overall_score}
                      />
                    ) : (
                      <span className="text-xs text-slate-400">
                        Not analyzed
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {overview.latest_health_score ? (
                      <ScoreBadge
                        score={
                          overview.latest_health_score.hallucination_risk_score
                        }
                      />
                    ) : (
                      <span className="text-xs text-slate-400">—</span>
                    )}
                    {overview.unsupported_claim_count > 0 ? (
                      <span className="ml-2 text-xs text-slate-500">
                        {overview.unsupported_claim_count} unsupported claim
                        {overview.unsupported_claim_count === 1 ? "" : "s"}
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {overview.detection_event_count}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      href={`/sessions/${overview.session.id}`}
                      className="inline-flex items-center text-slate-300 transition group-hover:text-indigo-500"
                      aria-label={`Open ${overview.session.name}`}
                    >
                      <ChevronRightIcon className="h-4 w-4" />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}

function SummaryStat({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: ComponentType<{ className?: string }>;
  accent: string;
}) {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
        <Icon className={`h-4 w-4 ${accent}`} />
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold tracking-tight text-slate-900">
        {value}
      </div>
    </div>
  );
}
