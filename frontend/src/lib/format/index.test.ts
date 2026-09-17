import { describe, expect, it } from "vitest";
import {
  compareClassificationSeverity,
  compareSeverityDesc,
  formatDuration,
  formatScorePercent,
} from "@/lib/format";

describe("formatDuration", () => {
  it("renders seconds for sub-minute durations", () => {
    const start = "2024-01-01T00:00:00Z";
    const end = "2024-01-01T00:00:45Z";
    expect(formatDuration(start, end)).toBe("45s");
  });

  it("renders minutes and seconds", () => {
    const start = "2024-01-01T00:00:00Z";
    const end = "2024-01-01T00:05:30Z";
    expect(formatDuration(start, end)).toBe("5m 30s");
  });

  it("renders hours and minutes", () => {
    const start = "2024-01-01T00:00:00Z";
    const end = "2024-01-01T02:15:00Z";
    expect(formatDuration(start, end)).toBe("2h 15m");
  });

  it("renders days and hours", () => {
    const start = "2024-01-01T00:00:00Z";
    const end = "2024-01-03T04:00:00Z";
    expect(formatDuration(start, end)).toBe("2d 4h");
  });

  it("treats a null end as ongoing (uses current time)", () => {
    const start = new Date(Date.now() - 10_000).toISOString();
    const result = formatDuration(start, null);
    expect(result).toMatch(/^\d+s$/);
  });
});

describe("formatScorePercent", () => {
  it("renders a 0-1 score as a rounded percentage", () => {
    expect(formatScorePercent(0.734)).toBe("73%");
    expect(formatScorePercent(1)).toBe("100%");
    expect(formatScorePercent(0)).toBe("0%");
  });

  it("renders a placeholder for missing scores", () => {
    expect(formatScorePercent(null)).toBe("—");
    expect(formatScorePercent(undefined)).toBe("—");
  });
});

describe("compareSeverityDesc", () => {
  it("orders critical before info", () => {
    expect(compareSeverityDesc("critical", "info")).toBeLessThan(0);
    expect(compareSeverityDesc("info", "critical")).toBeGreaterThan(0);
  });

  it("sorts a mixed list from most to least severe", () => {
    const severities = ["low", "critical", "info", "high", "medium"] as const;
    const sorted = [...severities].sort(compareSeverityDesc);
    expect(sorted).toEqual(["critical", "high", "medium", "low", "info"]);
  });
});

describe("compareClassificationSeverity", () => {
  it("orders high-confidence hallucination before unsupported", () => {
    expect(
      compareClassificationSeverity(
        "high_confidence_hallucination",
        "unsupported",
      ),
    ).toBeLessThan(0);
  });

  it("orders possible_hallucination before insufficient_evidence", () => {
    expect(
      compareClassificationSeverity(
        "possible_hallucination",
        "insufficient_evidence",
      ),
    ).toBeLessThan(0);
  });
});
