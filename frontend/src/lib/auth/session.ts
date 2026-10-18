import type { z } from "zod";
import { bootstrapCsrf, loginAccount, revokeSession, rotateSession, type LoginInput } from "@/lib/api/auth";
import { ApiClient, ApiError, apiErrorMessage } from "@/lib/api/client";
import { userSchema, type Tokens, type User } from "@/types/api";
import { withSessionLock } from "./lock";

type Status = "restoring" | "authenticated" | "anonymous" | "unavailable";
export type AuthSnapshot = { status: Status; user: User | null; error: string | null; notice: string | null };
const initial: AuthSnapshot = { status: "restoring", user: null, error: null, notice: null };

export class SessionManager {
  private access: string | null = null;
  private expiresAt = 0;
  private generation = 0;
  private snapshot: AuthSnapshot = initial;
  private listeners = new Set<() => void>();
  private restorePromise: Promise<void> | null = null;
  private refreshPromise: Promise<void> | null = null;
  private channel: BroadcastChannel | null = null;

  constructor(private readonly api = new ApiClient(), private readonly lock = withSessionLock) {}
  getSnapshot = () => this.snapshot;
  getServerSnapshot = () => initial;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private publish(value: AuthSnapshot) { this.snapshot = value; this.listeners.forEach(listener => listener()); }
  private clear(status: "anonymous" | "unavailable", error: string | null = null, notice: string | null = null) {
    this.access = null; this.expiresAt = 0;
    this.publish({ status, user: null, error, notice });
  }
  connect() {
    if (typeof BroadcastChannel !== "undefined" && !this.channel) {
      this.channel = new BroadcastChannel("codemate-session-events");
      this.channel.onmessage = event => {
        if (event.data === "signed-out") { this.generation++; this.clear("anonymous"); }
        if (event.data === "signed-in") {
          this.generation++; this.access = null; this.expiresAt = 0;
          this.publish(initial); void this.restore().then(() => {
            if (this.snapshot.status === "restoring") void this.restore();
          });
        }
      };
    }
  }
  disconnect() { this.channel?.close(); this.channel = null; }
  private accept(tokens: Tokens) { this.access = tokens.access_token; this.expiresAt = Date.now() + tokens.expires_in * 1000; }
  private async profile() {
    return this.api.request("/api/v1/auth/me", { headers: { Authorization: `Bearer ${this.access}` } }, userSchema);
  }
  renewalDelay = () => Math.max(1000, this.expiresAt - Date.now() - 5000);
  restore(): Promise<void> {
    if (this.restorePromise) return this.restorePromise;
    const generation = this.generation;
    this.restorePromise = (async () => {
      try {
        if (!this.access || Date.now() >= this.expiresAt - 5000) await this.refresh();
        if (generation !== this.generation) return;
        const user = await this.profile();
        if (generation === this.generation) this.publish({ status: "authenticated", user, error: null, notice: null });
      } catch (error) {
        if (generation !== this.generation) return;
        if (error instanceof ApiError && error.status === 401) this.clear("anonymous");
        else this.publish({ status: "unavailable", user: null, error: apiErrorMessage(error), notice: null });
      }
    })().finally(() => { this.restorePromise = null; });
    return this.restorePromise;
  }
  private refresh(): Promise<void> {
    if (this.refreshPromise) return this.refreshPromise;
    const generation = this.generation;
    this.refreshPromise = this.lock(async () => {
      const { csrf_token } = await bootstrapCsrf(this.api);
      const tokens = await rotateSession(this.api, csrf_token);
      if (generation === this.generation) this.accept(tokens);
    }).finally(() => { this.refreshPromise = null; });
    return this.refreshPromise;
  }
  async login(input: LoginInput): Promise<void> {
    const generation = ++this.generation;
    await this.lock(async () => {
      const tokens = await loginAccount(this.api, input);
      if (generation !== this.generation) return;
      this.accept(tokens);
      const user = await this.profile();
      if (generation === this.generation) {
        this.publish({ status: "authenticated", user, error: null, notice: null });
        this.channel?.postMessage("signed-in");
      }
    });
  }
  async logout(): Promise<boolean> {
    ++this.generation;
    this.clear("anonymous");
    this.channel?.postMessage("signed-out");
    try {
      await this.lock(async () => {
        const { csrf_token } = await bootstrapCsrf(this.api);
        await revokeSession(this.api, csrf_token);
      });
      this.publish({ status: "anonymous", user: null, error: null, notice: "Signed out. The server session was revoked." });
      return true;
    } catch {
      this.publish({ status: "anonymous", user: null, error: null, notice: "Signed out locally. Server revocation could not be confirmed; the cookie session may restore after reload." });
      return false;
    }
  }
  async post<T>(path: "/api/v1/auth/github/connect" | "/api/v1/auth/github/disconnect" | `/api/v1/auth/ai/${string}` | `/api/v1/auth/voice/${string}` | `/api/v1/auth/automation/${string}`,  schema: z.ZodType<T> | undefined, body?: unknown): Promise<T> {
    const generation = this.generation;
    const current = () => {
      if (generation !== this.generation || !this.access) throw new ApiError("The session changed. Please sign in again.", 401);
    };
    try {
      current();
      if (Date.now() >= this.expiresAt - 5000) await this.refresh();
      return await this.lock(async () => {
        current();
        const { csrf_token } = await bootstrapCsrf(this.api);
        current();
        const value = await this.api.request(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body), headers: { Authorization: `Bearer ${this.access}`, "X-CodeMate-Request": "1", "X-CSRF-Token": csrf_token } }, schema);
        current();
        return value;
      });
    } catch (error) {
      if (generation === this.generation && error instanceof ApiError && error.status === 401) {
        this.generation++; this.clear("anonymous", null, "Your session has expired. Please sign in again.");
      }
      throw error;
    }
  }
  async uploadAudio(body: Blob, language: "en" | "fr" | "auto", schema: z.ZodType<{ text: string; language: string }>, signal?: AbortSignal) {
    const generation = this.generation;
    const current = () => { if (generation !== this.generation || !this.access) throw new ApiError("The session changed. Please sign in again.", 401); };
    try {
      current();
      if (Date.now() >= this.expiresAt - 5000) await this.refresh();
      return await this.lock(async () => {
        current();
        const { csrf_token } = await bootstrapCsrf(this.api);
        current();
        const result = await this.api.request(`/api/v1/auth/voice/transcribe?language=${language}`, { method: "POST", body, signal, headers: { Authorization: `Bearer ${this.access}`, "X-CodeMate-Request": "1", "X-CSRF-Token": csrf_token, "Content-Type": body.type } }, schema);
        current(); return result;
      });
    } catch (error) {
      if (generation === this.generation && error instanceof ApiError && error.status === 401) {
        this.generation++; this.clear("anonymous", null, "Your session has expired. Please sign in again.");
      }
      throw error;
    }
  }

  // Only idempotent authenticated GETs get one refresh and one retry.
  async get<T>(path: string, schema: z.ZodType<T>, signal?: AbortSignal): Promise<T> {
    const generation = this.generation;
    const assertCurrent = () => {
      if (generation !== this.generation || !this.access) throw new ApiError("The session changed. Please sign in again.", 401);
    };
    const request = async () => {
      assertCurrent();
      const result = await this.api.request(path, { signal, headers: { Authorization: `Bearer ${this.access}` } }, schema);
      assertCurrent();
      return result;
    };
    try {
      assertCurrent();
      if (Date.now() >= this.expiresAt - 5000) await this.refresh();
      const token = this.access;
      try { return await request(); }
      catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401 || generation !== this.generation) throw error;
        if (this.access === token) await this.refresh();
        return await request();
      }
    } catch (error) {
      if (generation === this.generation && error instanceof ApiError && error.status === 401) {
        this.generation++; this.clear("anonymous", null, "Your session has expired. Please sign in again.");
      }
      throw error;
    }
  }
}
