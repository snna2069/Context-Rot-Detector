import { apiFetch } from "@/lib/api/client";
import type { AgentSession, SessionOverview, SessionTimelineResponse } from "@/lib/api/types";

export function listSessionOverviews(params?: {
  limit?: number;
  offset?: number;
}): Promise<SessionOverview[]> {
  return apiFetch<SessionOverview[]>("/dashboard/sessions", {
    query: { limit: params?.limit, offset: params?.offset },
  });
}

export function getSession(sessionId: string): Promise<AgentSession> {
  return apiFetch<AgentSession>(`/sessions/${sessionId}`);
}

export function getSessionTimeline(
  sessionId: string,
): Promise<SessionTimelineResponse> {
  return apiFetch<SessionTimelineResponse>(`/sessions/${sessionId}/timeline`);
}
