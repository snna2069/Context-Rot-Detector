import { formatScorePercent } from "@/lib/format";

/** Color thresholds are intentionally coarse and only used for a quick
 * visual scan; the underlying numeric score (always shown alongside) is
 * the actual data, not the color. */
function scoreColorClass(score: number | null | undefined): string {
  if (score === null || score === undefined) {
    return "bg-slate-100 text-slate-500 border-slate-300";
  }
  if (score >= 0.75) return "bg-emerald-50 text-emerald-700 border-emerald-300";
  if (score >= 0.5) return "bg-amber-50 text-amber-800 border-amber-300";
  return "bg-red-50 text-red-800 border-red-300";
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
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium ${scoreColorClass(score)}`}
      title={label}
    >
      {label ? <span className="text-[10px] uppercase opacity-70">{label}</span> : null}
      {formatScorePercent(score)}
    </span>
  );
}
