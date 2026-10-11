import type { z } from "zod";

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number, public readonly kind: "http" | "network" | "timeout" | "protocol" = "http", public readonly code?: string, public readonly retryAfter?: number) {
    super(message); this.name = "ApiError";
  }
}

export function apiErrorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Something went wrong. Please try again.";
}

export class ApiClient {
  readonly baseUrl: string;
  constructor(baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000", private readonly timeoutMs = 8000) {
    const url = new URL(baseUrl);
    if (!["http:", "https:"].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
      throw new Error("NEXT_PUBLIC_API_URL must be a public HTTP(S) URL without credentials.");
    }
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  async request<T>(path: string, options: RequestInit = {}, schema?: z.ZodType<T>): Promise<T> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), path.includes("/github/") ? 30000 : this.timeoutMs);
    const headers = new Headers(options.headers);
    headers.set("Accept", "application/json");
    if (options.body) headers.set("Content-Type", "application/json");
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options, headers, credentials: "include", cache: "no-store", signal: controller.signal,
      });
      if (!response.ok) {
        if (path.includes("/github/")) {
          const body = await response.json().catch(() => null);
          const detail = body?.detail;
          if (typeof detail?.code === "string" && /^GITHUB_[A-Z_]+$/.test(detail.code) && typeof detail.message === "string") {
            throw new ApiError(detail.message.slice(0, 500), response.status, "http", detail.code, typeof detail.retry_after === "number" ? detail.retry_after : undefined);
          }
        }
        const messages: Record<number, string> = {
          401: "Your session has expired. Please sign in again.",
          403: "You do not have permission to access this resource.",
          409: "That email or username is already registered.",
          422: "Check the information you entered and try again.",
          429: "Too many sign-in attempts. Please wait a few minutes and try again.",
        };
        throw new ApiError(messages[response.status] || "The service could not complete this request. Please try again.", response.status);
      }
      if (response.status === 204) return undefined as T;
      let data: unknown;
      try { data = await response.json(); } catch { throw new ApiError("The service returned an unexpected response.", undefined, "protocol"); }
      if (!schema) return data as T;
      const parsed = schema.safeParse(data);
      if (!parsed.success) throw new ApiError("The service returned an unexpected response.", undefined, "protocol");
      return parsed.data;
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (controller.signal.aborted) throw new ApiError("The request timed out. Please try again.", undefined, "timeout");
      throw new ApiError("Cannot reach the API. Check your connection and try again.", undefined, "network");
    } finally { clearTimeout(timer); }
  }
}
export const apiClient = new ApiClient();
