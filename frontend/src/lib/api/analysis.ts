import { apiFetch } from "@/lib/api/client";
import {
  arrayOf,
  parseAnalysisRun,
  parseAnalysisStatus,
  parseHealthScore,
} from "@/lib/api/validate";
import type {
  AnalysisRun,
  AnalysisRunResult,
  AnalysisStatus,
  ContextHealthScore,
  DetectionEvent,
  HealthTrend,
} from "@/lib/api/types";

/** Bounds the request so a huge session cannot be fetched unbounded. */
const DETECTION_EVENT_LIMIT = 500;

export function listDetectionEvents(sessionId: string): Promise<DetectionEvent[]> {
  return apiFetch<DetectionEvent[]>(`/sessions/${sessionId}/detection-events`, {
    query: { limit: DETECTION_EVENT_LIMIT },
  });
}

/** The cap applied by `listDetectionEvents`, so callers can tell the
 * user when a list may have been truncated. */
export const detectionEventLimit = DETECTION_EVENT_LIMIT;

export function listHealthScores(
  sessionId: string,
): Promise<ContextHealthScore[]> {
  return apiFetch<ContextHealthScore[]>(`/sessions/${sessionId}/health-scores`, {
    parse: arrayOf(parseHealthScore, "an array of health scores"),
  });
}

/** Recent analysis runs, newest first. Used to tell whether the stored
 * results came from a run where every detector actually completed. */
export function listAnalysisRuns(sessionId: string): Promise<AnalysisRun[]> {
  return apiFetch<AnalysisRun[]>(`/sessions/${sessionId}/analysis-runs`, {
    parse: arrayOf(parseAnalysisRun, "an array of analysis runs"),
  });
}

/** Whether the stored analysis still covers every ingested message. */
export function getAnalysisStatus(sessionId: string): Promise<AnalysisStatus> {
  return apiFetch<AnalysisStatus>(`/sessions/${sessionId}/analysis-status`, {
    parse: parseAnalysisStatus,
  });
}

export function getHealthTrend(sessionId: string): Promise<HealthTrend> {
  return apiFetch<HealthTrend>(`/sessions/${sessionId}/health-trend`);
}

/** Triggers a new analysis run. Called from the client (a real mutation,
 * not a page load), so it is kept separate from the read-only functions
 * above. */
export function analyzeSession(sessionId: string): Promise<AnalysisRunResult> {
  return apiFetch<AnalysisRunResult>(`/sessions/${sessionId}/analyze`, {
    method: "POST",
  });
}
