import { apiFetch } from "@/lib/api/client";
import type {
  AnalysisRun,
  AnalysisRunResult,
  ContextHealthScore,
  DetectionEvent,
  HealthTrend,
} from "@/lib/api/types";

export function listDetectionEvents(sessionId: string): Promise<DetectionEvent[]> {
  return apiFetch<DetectionEvent[]>(`/sessions/${sessionId}/detection-events`);
}

export function listHealthScores(
  sessionId: string,
): Promise<ContextHealthScore[]> {
  return apiFetch<ContextHealthScore[]>(`/sessions/${sessionId}/health-scores`);
}

/** Recent analysis runs, newest first. Used to tell whether the stored
 * results came from a run where every detector actually completed. */
export function listAnalysisRuns(sessionId: string): Promise<AnalysisRun[]> {
  return apiFetch<AnalysisRun[]>(`/sessions/${sessionId}/analysis-runs`);
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
