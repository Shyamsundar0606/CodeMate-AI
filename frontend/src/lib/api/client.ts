import type { z } from "zod";
import { AUDIO_BYTES, InputLimitError, readBounded, readJSON } from "./limits";

export class ApiError extends Error {
  constructor(message: string, public readonly status?: number, public readonly kind: "http" | "network" | "timeout" | "protocol" = "http", public readonly code?: string, public readonly retryAfter?: number, public requestId?: string) {
    super(message); this.name = "ApiError";
  }
}

export function apiErrorMessage(error: unknown): string {
  return error instanceof ApiError ? `${error.message}${error.requestId ? ` (Request ${error.requestId})` : ""}` : "Something went wrong. Please try again.";
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
    const timer = setTimeout(() => controller.abort(), (path.includes("/sandbox/") || path.includes("/automation/") || path.includes("/github/") || (path.includes("/ai/") || path.includes("/voice/"))) ? ((path.includes("/voice/") || path.includes("/automation/")) ? 180000 : 30000) : this.timeoutMs);
    const abort = () => controller.abort();
    if (options.signal?.aborted) controller.abort();
    options.signal?.addEventListener("abort", abort, { once: true });
    const headers = new Headers(options.headers);
    headers.set("X-Correlation-ID", crypto.randomUUID());
    headers.set("Accept", "application/json");
    if (options.body && !(options.body instanceof Blob)) headers.set("Content-Type", "application/json");
    let requestId: string | undefined;
    try {
      const response = await fetch(`${this.baseUrl}${path}`, {
        ...options, headers, credentials: "include", cache: "no-store", signal: controller.signal,
      });
      const suppliedId = response.headers.get("X-Request-ID");
      if (suppliedId && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(suppliedId)) requestId = suppliedId;
      if (!response.ok) {
        if (path.includes("/sandbox/") || path.includes("/automation/") || path.includes("/github/") || (path.includes("/ai/") || path.includes("/voice/"))) {
          const body = await readJSON(response).catch(error => { if (error instanceof InputLimitError) throw error; return null; });
          const detail = body && typeof body === "object" && "detail" in body ? body.detail as { code?: unknown; message?: unknown; retry_after?: unknown } : undefined;
          if (typeof detail?.code === "string" && /^(?:GITHUB|AI|VOICE|AUTOMATION|SANDBOX)_[A-Z_]+$/.test(detail.code) && typeof detail.message === "string") {
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
        await response.body?.cancel().catch(() => undefined);
        throw new ApiError(messages[response.status] || "The service could not complete this request. Please try again.", response.status);
      }
      if (response.headers.get("content-type")?.startsWith("audio/wav")) {
        if (schema || !path.endsWith("/voice/speech")) throw new ApiError("The service returned an unexpected response.", undefined, "protocol");
        const bytes = await readBounded(response, AUDIO_BYTES);
        return new Blob([bytes as BlobPart], { type: "audio/wav" }) as T;
      }
      if (response.status === 204) return undefined as T;
      let data: unknown;
      try { data = await readJSON(response); } catch { throw new ApiError("The service returned an unexpected or oversized response.", undefined, "protocol"); }
      if (!schema) return data as T;
      const parsed = schema.safeParse(data);
      if (!parsed.success) throw new ApiError("The service returned an unexpected response.", undefined, "protocol");
      return parsed.data;
    } catch (error) {
      if (error instanceof InputLimitError) throw new ApiError("The service returned an oversized response.", undefined, "protocol", undefined, undefined, requestId);
      if (error instanceof ApiError) { error.requestId = requestId; throw error; }
      if (controller.signal.aborted) throw new ApiError("The request timed out. Please try again.", undefined, "timeout");
      throw new ApiError("Cannot reach the API. Check your connection and try again.", undefined, "network");
    } finally { clearTimeout(timer); options.signal?.removeEventListener("abort", abort); }
  }
}
export const apiClient = new ApiClient();
