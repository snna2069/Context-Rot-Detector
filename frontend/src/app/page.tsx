import Link from "next/link";
import { listSessionOverviews } from "@/lib/api/sessions";
import { StatusBadge } from "@/components/StatusBadge";
import { ScoreBadge } from "@/components/ScoreBadge";
import { EmptyState } from "@/components/EmptyState";
import { formatDuration } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function SessionsListPage() {
  const overviews = await listSessionOverviews({ limit: 100 });

  return (
    <main className="mx-auto w-full max-w-6xl px-6 py-10">
      <div className="mb-6 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-950">
            Sessions
          </h1>
          <p className="mt-1 text-sm text-slate-600">
            Long-running agent sessions currently tracked by the detector.
          </p>
        </div>
      </div>

      {overviews.length === 0 ? (
        <EmptyState
          title="No sessions yet"
          description="Ingest a session through the API to see it appear here."
        />
      ) : (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3 font-medium">Session</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Duration</th>
                <th className="px-4 py-3 font-medium">Messages</th>
                <th className="px-4 py-3 font-medium">Context health</th>
                <th className="px-4 py-3 font-medium">Hallucination risk</th>
                <th className="px-4 py-3 font-medium">Detections</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {overviews.map((overview) => (
                <tr key={overview.session.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/sessions/${overview.session.id}`}
                      className="font-medium text-slate-900 hover:underline"
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
