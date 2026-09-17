import { apiFetch } from "@/lib/api/client";
import type {
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
