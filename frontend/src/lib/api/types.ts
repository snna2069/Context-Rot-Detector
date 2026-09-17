/**
 * TypeScript types mirroring the backend's Pydantic response schemas
 * (see `backend/app/schemas/`). Field names intentionally match the JSON
 * the API actually returns (snake_case) rather than being remapped to
 * camelCase, so there is no hidden translation layer between what the
 * network sends and what components render.
 */

export type SessionStatus = "active" | "completed" | "failed" | "archived";

export type MessageRole = "system" | "developer" | "user" | "assistant" | "tool";

export type DetectionSeverity = "info" | "low" | "medium" | "high" | "critical";

export type DetectionType =
  | "contradiction"
  | "instruction_drift"
  | "stale_context"
  | "repetition"
  | "unsupported_claim"
  | "tool_result_misuse"
  | "context_growth"
  | "omission"
  | "topic_drift"
  | "behavior_shift"
  | "fact_loss";

export type AnalysisRunStatus = "pending" | "running" | "completed" | "failed";

/**
 * The six evidence-based classifications from the Phase 5 semantic layer
 * (see `app.services.llm.types.EvidenceClassification`). Only the last
 * four are ever emitted as a `DetectionEvent` -- SUPPORTED and
 * INSUFFICIENT_EVIDENCE are "no news" and never surfaced as a signal --
 * but all six are modeled here so the UI never has to guess at an
 * unrecognized value.
 */
export type HallucinationClassification =
  | "supported"
  | "contradicted"
  | "unsupported"
  | "possible_hallucination"
  | "high_confidence_hallucination"
  | "insufficient_evidence";

export interface AgentSession {
  id: string;
  name: string;
  status: SessionStatus;
  started_at: string;
  ended_at: string | null;
  created_at: string;
  updated_at: string;
  session_metadata: Record<string, unknown>;
}

export interface Message {
  id: string;
  session_id: string;
  sequence_number: number;
  role: MessageRole;
  content: string;
  created_at: string;
  provider_message_id: string | null;
  message_metadata: Record<string, unknown>;
}

export interface ToolResult {
  id: string;
  session_id: string;
  tool_call_id: string;
  output: Record<string, unknown>;
  is_error: boolean;
  created_at: string;
}

export interface ToolCall {
  id: string;
  session_id: string;
  message_id: string;
  call_index: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  created_at: string;
}

export interface ToolCallTimelineEntry extends ToolCall {
  result: ToolResult | null;
}

export interface MessageTimelineEntry extends Message {
  tool_calls: ToolCallTimelineEntry[];
}

export interface SessionTimelineResponse {
  session: AgentSession;
  messages: MessageTimelineEntry[];
}

export interface DetectionEvidence {
  id: string;
  message_id: string | null;
  tool_call_id: string | null;
  tool_result_id: string | null;
  context_snapshot_id: string | null;
  important_fact_id: string | null;
  evidence_role: string;
  excerpt: string | null;
}

export interface DetectionEvent {
  id: string;
  session_id: string;
  analysis_run_id: string;
  detection_type: DetectionType;
  severity: DetectionSeverity;
  confidence: number;
  explanation: string;
  timestamp: string;
  evidence: DetectionEvidence[];
  related_message_ids: string[];
  metadata: Record<string, unknown>;
}

export interface ContextHealthScore {
  id: string;
  session_id: string;
  analysis_run_id: string;
  overall_score: number;
  relevance_score: number | null;
  consistency_score: number | null;
  instruction_adherence_score: number | null;
  information_retention_score: number | null;
  tool_utilization_score: number | null;
  hallucination_risk_score: number | null;
  measured_at: string;
}

export interface AnalysisRun {
  id: string;
  session_id: string;
  analysis_version: string;
  status: AnalysisRunStatus;
  input_sequence_start: number | null;
  input_sequence_end: number | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface AnalysisRunResult {
  analysis_run: AnalysisRun;
  detection_events: DetectionEvent[];
  health_score: ContextHealthScore | null;
}

export interface HealthTrendPoint {
  measured_at: string;
  overall_score: number;
  context_length: number | null;
}

export type HealthTrendDirection = "improving" | "stable" | "degrading";

export type HealthChangeDirection = "initial" | "increased" | "decreased" | "unchanged";

export interface HealthChangeExplanation {
  direction: HealthChangeDirection;
  score_delta: number | null;
  reasons: string[];
  headline: string;
}

export interface HealthTrend {
  direction: HealthTrendDirection;
  slope_per_checkpoint: number;
  slope_per_context_length: number | null;
  is_degrading_with_length: boolean;
  summary: string;
  points: HealthTrendPoint[];
  explanation: HealthChangeExplanation;
}

export interface SessionOverview {
  session: AgentSession;
  message_count: number;
  detection_event_count: number;
  unsupported_claim_count: number;
  latest_health_score: ContextHealthScore | null;
}
