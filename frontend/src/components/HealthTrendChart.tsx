import type { HealthTrendPoint } from "@/lib/api/types";

const WIDTH = 640;
const HEIGHT = 180;
const PADDING = 24;

/** A minimal, dependency-free SVG line chart for a bounded number of
 * health-score checkpoints. A full charting library (Recharts, Chart.js,
 * D3, ...) was deliberately not added: the data set per session is small,
 * the chart requirement is a single line with reference bands, and a
 * ~90-line component covers it without a new dependency. */
export function HealthTrendChart({ points }: { points: HealthTrendPoint[] }) {
  if (points.length === 0) {
    return null;
  }

  const scores = points.map((p) => p.overall_score);
  const minScore = Math.min(0, ...scores);
  const maxScore = Math.max(1, ...scores);
  const range = maxScore - minScore || 1;

  const usableWidth = WIDTH - PADDING * 2;
  const usableHeight = HEIGHT - PADDING * 2;

  const toX = (index: number) =>
    points.length === 1
      ? PADDING + usableWidth / 2
      : PADDING + (index / (points.length - 1)) * usableWidth;
  const toY = (score: number) =>
    PADDING + usableHeight - ((score - minScore) / range) * usableHeight;

  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"}${toX(index)},${toY(point.overall_score)}`)
    .join(" ");

  const areaPath =
    `${linePath} L${toX(points.length - 1)},${toY(minScore)} L${toX(0)},${toY(minScore)} Z`;

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      className="w-full"
      role="img"
      aria-label="Context health score over time"
    >
      <defs>
        <linearGradient id="health-line-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.22} />
          <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
        </linearGradient>
      </defs>

      {/* Reference bands roughly matching the badge color thresholds used
       * elsewhere (>=0.75 healthy, >=0.5 watch, below that concerning). */}
      <rect
        x={PADDING}
        y={toY(1)}
        width={usableWidth}
        height={toY(0.75) - toY(1)}
        fill="#ecfdf5"
      />
      <rect
        x={PADDING}
        y={toY(0.75)}
        width={usableWidth}
        height={toY(0.5) - toY(0.75)}
        fill="#fffbeb"
      />
      <rect
        x={PADDING}
        y={toY(0.5)}
        width={usableWidth}
        height={toY(minScore) - toY(0.5)}
        fill="#fef2f2"
      />

      <path d={areaPath} fill="url(#health-line-fill)" stroke="none" />
      <path
        d={linePath}
        fill="none"
        stroke="#4338ca"
        strokeWidth={2.5}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      {points.map((point, index) => (
        <circle
          key={point.measured_at}
          cx={toX(index)}
          cy={toY(point.overall_score)}
          r={index === points.length - 1 ? 4.5 : 3}
          fill="#ffffff"
          stroke="#4338ca"
          strokeWidth={2}
          className="transition-all"
        >
          <title>
            {new Date(point.measured_at).toLocaleString()}: {Math.round(point.overall_score * 100)}%
          </title>
        </circle>
      ))}
    </svg>
  );
}
