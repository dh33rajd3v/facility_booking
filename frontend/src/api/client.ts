export const API_BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ?? "http://localhost:8000/api/v1";

/** Error thrown for non-2xx responses, carrying the backend's `{error: {code, message}}` payload. */
export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      method: "GET",
      headers: { Accept: "application/json", ...(init?.headers ?? {}) },
      credentials: "include",
    });
  } catch {
    throw new ApiError(0, "NETWORK_ERROR", "Could not reach the booking server. Is the backend running?");
  }

  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const err = (body as { error?: { code?: string; message?: string; details?: Record<string, unknown> } } | null)
      ?.error;
    throw new ApiError(
      response.status,
      err?.code ?? "HTTP_ERROR",
      err?.message ?? `Request failed with status ${response.status}.`,
      err?.details ?? {},
    );
  }
  return body as T;
}
