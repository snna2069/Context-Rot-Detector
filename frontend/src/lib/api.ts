export type HealthResponse = {
  status: string;
};

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(`${apiBaseUrl}/health`, {
    headers: { Accept: "application/json" },
    next: { revalidate: 10 },
  });

  if (!response.ok) {
    throw new Error(`Backend health request failed: ${response.status}`);
  }

  return response.json() as Promise<HealthResponse>;
}
