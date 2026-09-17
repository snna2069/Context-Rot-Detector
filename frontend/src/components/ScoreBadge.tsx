import { formatScorePercent } from "@/lib/format";

/** Color thresholds are intentionally coarse and only used for a quick
 * visual scan; the underlying numeric score (always shown alongside) is
 * the actual data, not the color. */
function scoreColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) {
    return "bg-slate-100 text-slate-500 ring-slate-300";
  }
  if (score >= 0.75) return "bg-emerald-50 text-emerald-700 ring-emerald-200";
  if (score >= 0.5) return "bg-amber-50 text-amber-800 ring-amber-200";
  return "bg-red-50 text-red-800 ring-red-200";
}

function scoreDotClass(score: number | null | undefined): string {
  if (score === null || score === undefined) return "bg-slate-300";
  if (score >= 0.75) return "bg-emerald-500";
  if (score >= 0.5) return "bg-amber-500";
  return "bg-red-500";
}

export function ScoreBadge({
  score,
  label,
}: {
  score: number | null | undefined;
  label?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${scoreColorClass(score)}`}
      title={label}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${scoreDotClass(score)}`} />
      {label ? <span className="text-[10px] font-medium uppercase opacity-70">{label}</span> : null}
      {formatScorePercent(score)}
    </span>
  );
}
