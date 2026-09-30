import { describe, expect, it, vi, afterEach } from "vitest";
import { ApiError, apiFetch } from "@/lib/api/client";
import {
  arrayOf,
  parseAnalysisRun,
  parseAnalysisStatus,
  parseHealthScore,
} from "@/lib/api/validate";

/** Asserts the request rejected, and narrows the error for assertions. */
async function expectApiError(promise: Promise<unknown>): Promise<ApiError> {
  try {
    await promise;
  } catch (error) {
    return error as ApiError;
  }
  throw new Error("expected the request to reject, but it resolved");
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("apiFetch", () => {
  it("returns the parsed JSON body on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ id: "s1" })),
    );

    await expect(apiFetch("/sessions/s1")).resolves.toEqual({ id: "s1" });
  });

  it("wraps a network failure in an ApiError with status 0", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("boom")));

    const error = await expectApiError(apiFetch("/sessions"));

    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(0);
    expect(error.message).toContain("Could not reach the backend");
  });

  it("reports a timeout distinctly from an unreachable backend", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockRejectedValue(
          new DOMException("The operation timed out.", "TimeoutError"),
        ),
    );

    const error = await expectApiError(apiFetch("/sessions"));

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toContain("timed out");
  });

  it("passes an abort signal so a hung backend cannot hang forever", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse({}));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/sessions");

    expect(fetchMock.mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });

  it("surfaces the backend error detail on a non-2xx response", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          jsonResponse({ error: "conflict", detail: "retry the request" }, 409),
        ),
    );

    const error = await expectApiError(apiFetch("/sessions/s1/messages"));

    expect(error.status).toBe(409);
    expect(error.message).toContain("retry the request");
  });

  it("raises a clear ApiError when the body is not valid JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response("<html>502</html>", { status: 200 })),
    );

    const error = await expectApiError(apiFetch("/sessions"));

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toContain("not valid JSON");
  });

  it("rejects a response that fails validation instead of passing it on", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(jsonResponse({ not: "an array" })),
    );

    const error = await expectApiError(
      apiFetch("/sessions/s1/health-scores", {
        parse: arrayOf(parseHealthScore, "an array of health scores"),
      }),
    );

    expect(error).toBeInstanceOf(ApiError);
    expect(error.message).toContain("did not match the expected shape");
  });
});

describe("response validators", () => {
  const validRun = {
    id: "r1",
    session_id: "s1",
    analysis_version: "v1",
    status: "partial",
    input_sequence_start: 1,
    input_sequence_end: 3,
    error_message: "1 detector failed",
    failed_detectors: [{ detector: "claim_support", error: "timeout" }],
    created_at: "2026-01-01T00:00:00Z",
    completed_at: "2026-01-01T00:00:01Z",
  };

  it("accepts a well-formed analysis run", () => {
    expect(parseAnalysisRun(validRun).status).toBe("partial");
  });

  it("rejects an unknown run status rather than rendering it blindly", () => {
    expect(() => parseAnalysisRun({ ...validRun, status: "ok" })).toThrow(
      /known analysis run status/,
    );
  });

  it("defaults a missing failed_detectors to an empty array", () => {
    const withoutField = { ...validRun } as Partial<typeof validRun>;
    delete withoutField.failed_detectors;

    expect(parseAnalysisRun(withoutField).failed_detectors).toEqual([]);
  });

  it("preserves null dimension scores as null, not zero", () => {
    const score = parseHealthScore({
      id: "h1",
      session_id: "s1",
      analysis_run_id: "r1",
      overall_score: 0.9,
      relevance_score: 1,
      consistency_score: null,
      instruction_adherence_score: null,
      information_retention_score: 1,
      tool_utilization_score: 1,
      hallucination_risk_score: null,
      measured_at: "2026-01-01T00:00:00Z",
    });

    expect(score.consistency_score).toBeNull();
    expect(score.hallucination_risk_score).toBeNull();
    expect(score.overall_score).toBe(0.9);
  });

  it("rejects a health score whose dimension is the wrong type", () => {
    expect(() =>
      parseHealthScore({
        id: "h1",
        session_id: "s1",
        analysis_run_id: "r1",
        overall_score: 0.9,
        relevance_score: "high",
        consistency_score: null,
        instruction_adherence_score: null,
        information_retention_score: null,
        tool_utilization_score: null,
        hallucination_risk_score: null,
        measured_at: "2026-01-01T00:00:00Z",
      }),
    ).toThrow(/relevance_score/);
  });

  it("parses an analysis status with a nested run", () => {
    const status = parseAnalysisStatus({
      latest_run: validRun,
      analyzed_through_sequence: 3,
      latest_message_sequence: 5,
      message_count: 5,
      messages_since_analysis: 2,
      is_stale: true,
      has_been_analyzed: true,
    });

    expect(status.is_stale).toBe(true);
    expect(status.latest_run?.status).toBe("partial");
  });

  it("accepts an analysis status with no run yet", () => {
    const status = parseAnalysisStatus({
      latest_run: null,
      analyzed_through_sequence: null,
      latest_message_sequence: null,
      message_count: 0,
      messages_since_analysis: 0,
      is_stale: false,
      has_been_analyzed: false,
    });

    expect(status.latest_run).toBeNull();
  });

  it("rejects an analysis status missing is_stale", () => {
    expect(() =>
      parseAnalysisStatus({ latest_run: null, messages_since_analysis: 0 }),
    ).toThrow(/is_stale/);
  });
});
