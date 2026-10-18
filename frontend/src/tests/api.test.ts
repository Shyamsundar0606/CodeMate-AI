import { expect, it, vi } from "vitest";
import { ApiClient } from "@/lib/api/client";
import { registerAccount } from "@/lib/api/auth";
import { userSchema } from "@/types/api";
import { credentials, response, user } from "./fixtures";
it("sends only supported registration properties", async () => {
 const fetcher = vi.fn().mockResolvedValue(response(user, 201)); vi.stubGlobal("fetch", fetcher);
 const values = { ...credentials, username: "engineer", confirmPassword: credentials.password, role: "ADMIN" };
 await registerAccount(new ApiClient(), values);
 expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ ...credentials, username: "engineer" });
});
it.each([[409, "already registered"], [429, "Too many"], [403, "permission"]])("maps %s without exposing raw server details", async (status, message) => {
 vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: "private database exception" }, status)));
 await expect(new ApiClient().request("/test")).rejects.toMatchObject({ status, message: expect.stringContaining(message) });
});
it("rejects malformed profiles rather than trusting a 200", async () => {
 vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ role: "ADMIN" })));
 await expect(new ApiClient().request("/me", {}, userSchema)).rejects.toMatchObject({ kind: "protocol" });
});
it("aborts timed-out requests and never retries", async () => {
 const fetcher = vi.fn((_url, options) => new Promise((_resolve, reject) => options.signal.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError"))))); vi.stubGlobal("fetch", fetcher);
 await expect(new ApiClient("http://localhost:8000", 10).request("/slow")).rejects.toMatchObject({ kind: "timeout" }); expect(fetcher).toHaveBeenCalledTimes(1);
});
it.each(["https://user:secret@localhost", "javascript:alert(1)", "https://localhost?token=secret"])("rejects unsafe API base %s", url => expect(() => new ApiClient(url)).toThrow());

it.each([[422, "AUTOMATION_POLICY", "Model citations do not match the retrieved source evidence."], [429, "AUTOMATION_RATE_LIMIT", "Wait one minute before another automation request."]])("preserves safe automation errors (%s)", async (status, code, message) => {
 vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({ detail: { code, message } }, status)));
 await expect(new ApiClient().request("/api/v1/auth/automation/sessions/test/proposals")).rejects.toMatchObject({ status, code, message });
});
