import { apiFetch } from "@/lib/api/client";

export type HealthResponse = {
  status: string;
};

export function getHealth(): Promise<HealthResponse> {
  return apiFetch<HealthResponse>("/health");
}
