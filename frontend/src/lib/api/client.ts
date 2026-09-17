import { notFound } from "next/navigation";

/**
 * Base fetch wrapper for all backend calls.
 *
 * This is the single place that knows the backend base URL, attaches
 * standard headers, and turns a non-2xx response into a typed
 * `ApiError` -- callers (Server Components, route handlers, client
 * components) never construct URLs or parse raw JSON themselves.
 */

const apiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

/** True when the error represents "the resource does not exist" (404). */
export function isNotFound(error: unknown): error is ApiError {
  return error instanceof ApiError && error.status === 404;
}

/**
 * Awaits `promise`, converting a 404 `ApiError` into Next.js's `notFound()`
 * flow instead of letting it surface as a generic thrown error.
 *
 * Every route segment under `/sessions/[sessionId]` fetches session-scoped
 * data independently (layout and page render concurrently as separate
 * Server Components), so each of those fetches -- not just the layout's
 * -- needs this guard for an unknown session ID to consistently render
 * the route's `not-found.tsx` rather than Next's generic 404 fallback.
 */
export async function orNotFound<T>(promise: Promise<T>): Promise<T> {
  try {
    return await promise;
  } catch (error) {
    if (isNotFound(error)) {
      notFound();
    }
    throw error;
  }
}

interface RequestOptions {
  method?: "GET" | "POST";
  body?: unknown;
  /** Query string parameters; `undefined` values are omitted. */
  query?: Record<string, string | number | undefined>;
}

function buildUrl(path: string, query?: RequestOptions["query"]): string {
  const url = new URL(path, apiBaseUrl);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value !== undefined) {
        url.searchParams.set(key, String(value));
      }
    }
  }
  return url.toString();
}

export async function apiFetch<T>(
  path: string,
  options: RequestOptions = {},
): Promise<T> {
  const url = buildUrl(path, options.query);

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
      // The dashboard is an observability tool over live session data --
      // pages must reflect the latest ingested/analyzed state, so
      // responses are never cached.
      cache: "no-store",
    });
  } catch (cause) {
    throw new ApiError(
      0,
      `Could not reach the backend at ${apiBaseUrl}. Is it running?`,
      cause,
    );
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = undefined;
    }
    const detailMessage =
      detail && typeof detail === "object" && "detail" in detail
        ? String((detail as { detail: unknown }).detail)
        : response.statusText;
    throw new ApiError(
      response.status,
      `Request to ${path} failed (${response.status}): ${detailMessage}`,
      detail,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}
