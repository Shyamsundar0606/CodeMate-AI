import { beforeEach, describe, expect, it, vi } from "vitest";
import { z } from "zod";
import { ApiClient } from "@/lib/api/client";
import { SessionManager } from "@/lib/auth/session";
import { credentials, csrf, response, tokens, user } from "./fixtures";
const fetchMock = vi.fn<typeof fetch>();
function standard(url: RequestInfo | URL) {
  const path = String(url);
  if (path.endsWith("/csrf")) return Promise.resolve(response({ csrf_token: csrf }));
  if (path.endsWith("/login") || path.endsWith("/refresh")) return Promise.resolve(response(tokens));
  if (path.endsWith("/logout")) return Promise.resolve(response(null, 204));
  if (path.endsWith("/me")) return Promise.resolve(response(user));
  return Promise.resolve(response({ value: "safe" }));
}
const create = () => new SessionManager(new ApiClient("http://localhost:8000"));
const calls = (suffix: string) => fetchMock.mock.calls.filter(([url]) => String(url).endsWith(suffix));
beforeEach(() => { fetchMock.mockReset().mockImplementation(standard); vi.stubGlobal("fetch", fetchMock); });
describe("memory-only cookie session", () => {
  it("logs in only after obtaining an authenticated profile; never persists tokens", async () => {
    const session = create(); await session.login(credentials);
    expect(session.getSnapshot()).toMatchObject({ status: "authenticated", user });
    expect(calls("/me")[0][1]?.headers).toEqual(expect.any(Headers));
    expect(new Headers(calls("/me")[0][1]?.headers).get("Authorization")).toBe(`Bearer ${tokens.access_token}`);
    expect(localStorage.length).toBe(0); expect(sessionStorage.length).toBe(0);
    expect(JSON.stringify(session.getSnapshot())).not.toContain(tokens.access_token);
  });
  it("restores through CSRF bootstrap, rotation and profile, using credentials and no-store", async () => {
    const session = create(); await session.restore();
    expect(fetchMock.mock.calls.map(([url]) => String(url).split("/").pop())).toEqual(["csrf", "refresh", "me"]);
    const options = calls("/refresh")[0][1]!;
    expect(options).toMatchObject({ credentials: "include", cache: "no-store", method: "POST" });
    expect(new Headers(options.headers).get("X-CSRF-Token")).toBe(csrf);
    expect(new Headers(options.headers).get("X-CodeMate-Request")).toBe("1");
    expect(session.getSnapshot().status).toBe("authenticated");
  });
  it("coalesces concurrent restoration and avoids repeated profile requests", async () => {
    const session = create(); await Promise.all([session.restore(), session.restore(), session.restore()]);
    expect(calls("/refresh")).toHaveLength(1); expect(calls("/me")).toHaveLength(1);
  });
  it("rejects invalid credentials without publishing authentication", async () => {
    fetchMock.mockImplementation(url => String(url).endsWith("/login") ? Promise.resolve(response({}, 401)) : standard(url));
    const session = create(); await expect(session.login(credentials)).rejects.toMatchObject({ status: 401 });
    expect(session.getSnapshot().user).toBeNull(); expect(calls("/me")).toHaveLength(0);
  });
  it("makes an absent cookie anonymous without a refresh loop", async () => {
    fetchMock.mockResolvedValue(response({}, 401)); const session = create(); await session.restore();
    expect(session.getSnapshot().status).toBe("anonymous"); expect(fetchMock).toHaveBeenCalledTimes(1);
  });
  it("distinguishes outage from an absent or expired session and supports retry", async () => {
    fetchMock.mockRejectedValue(new TypeError("offline")); const session = create(); await session.restore();
    expect(session.getSnapshot()).toMatchObject({ status: "unavailable", user: null });
    fetchMock.mockImplementation(standard); await session.restore(); expect(session.getSnapshot().status).toBe("authenticated");
  });
  it("refreshes once for a 401 and retries only the authenticated GET", async () => {
    const session = create(); await session.login(credentials); let attempt = 0;
    fetchMock.mockImplementation(url => String(url).endsWith("/resource") ? Promise.resolve(response(attempt++ === 0 ? {} : { value: "safe" }, attempt === 1 ? 401 : 200)) : standard(url));
    await expect(session.get("/resource", z.object({ value: z.string() }))).resolves.toEqual({ value: "safe" });
    expect(calls("/resource")).toHaveLength(2); expect(calls("/refresh")).toHaveLength(1);
  });
  it("terminates after a repeated 401 and hides the expired profile", async () => {
    const session = create(); await session.login(credentials);
    fetchMock.mockImplementation(url => String(url).endsWith("/resource") ? Promise.resolve(response({}, 401)) : standard(url));
    await expect(session.get("/resource", z.unknown())).rejects.toMatchObject({ status: 401 });
    expect(calls("/resource")).toHaveLength(2); expect(calls("/refresh")).toHaveLength(1);
    expect(session.getSnapshot()).toMatchObject({ status: "anonymous", user: null });
  });
  it("does not refresh or discard a valid session on a 403", async () => {
    const session = create(); await session.login(credentials);
    fetchMock.mockImplementation(url => String(url).endsWith("/resource") ? Promise.resolve(response({}, 403)) : standard(url));
    await expect(session.get("/resource", z.unknown())).rejects.toMatchObject({ status: 403 });
    expect(calls("/refresh")).toHaveLength(0); expect(session.getSnapshot().status).toBe("authenticated");
  });
  it("does not refresh before ordinary requests, but renews near expiry", async () => {
    const clock = vi.spyOn(Date, "now").mockReturnValue(1000000); const session = create(); await session.login(credentials);
    await session.get("/resource", z.unknown()); expect(calls("/refresh")).toHaveLength(0);
    clock.mockReturnValue(1896000); await session.get("/resource", z.unknown()); expect(calls("/refresh")).toHaveLength(1);
  });
  it("coalesces simultaneous expired-token requests", async () => {
    const clock = vi.spyOn(Date, "now").mockReturnValue(1000000); const session = create(); await session.login(credentials);
    clock.mockReturnValue(1896000); await Promise.all([session.get("/one", z.unknown()), session.get("/two", z.unknown())]);
    expect(calls("/refresh")).toHaveLength(1);
  });
  it("clears authentication immediately and confirms revocation only after a 204", async () => {
    const session = create(); await session.login(credentials); const operation = session.logout();
    expect(session.getSnapshot()).toMatchObject({ status: "anonymous", user: null });
    await expect(operation).resolves.toBe(true);
    expect(new Headers(calls("/logout")[0][1]?.headers).get("X-CSRF-Token")).toBe(csrf);
    expect(session.getSnapshot().notice).toContain("server session was revoked");
    await expect(session.get("/resource", z.unknown())).rejects.toMatchObject({ status: 401 });
  });
  it("reports local-only signout when revocation fails", async () => {
    const session = create(); await session.login(credentials); fetchMock.mockRejectedValue(new TypeError("offline"));
    await expect(session.logout()).resolves.toBe(false);
    expect(session.getSnapshot()).toMatchObject({ status: "anonymous", user: null });
    expect(session.getSnapshot().notice).toContain("could not be confirmed");
  });
  it("cannot resurrect protected state from a restoration that finishes after logout", async () => {
    let release!: (value: Response) => void;
    fetchMock.mockImplementation(url => String(url).endsWith("/refresh") ? new Promise(resolve => { release = resolve; }) : standard(url));
    const session = create(); const restoring = session.restore();
    await vi.waitFor(() => expect(release).toBeTypeOf("function"));
    const logout = session.logout(); release(response(tokens)); await Promise.all([restoring, logout]);
    expect(session.getSnapshot().status).toBe("anonymous"); expect(calls("/me")).toHaveLength(0);
  });
  it("serializes CSRF bootstrap and mutations through the native cross-tab lock", async () => {
    const events: string[] = [];
    const request = vi.fn(async (_name: string, action: () => Promise<unknown>) => { events.push("locked"); return action(); });
    Object.defineProperty(navigator, "locks", { configurable: true, value: { request } });
    fetchMock.mockImplementation(url => { events.push(String(url).split("/").pop()!); return standard(url); });
    const session = create(); await session.restore();
    expect(request).toHaveBeenCalledWith("codemate-auth-cookie", expect.any(Function));
    expect(events.slice(0, 3)).toEqual(["locked", "csrf", "refresh"]);
    Object.defineProperty(navigator, "locks", { configurable: true, value: undefined });
  });
  it("broadcasts invalidation without secrets and clears state on another tab's logout", async () => {
    const postMessage = vi.fn();
    class Channel { static instances: Channel[] = []; onmessage: ((event: { data: string }) => void) | null = null; postMessage = postMessage; close = vi.fn(); constructor() { Channel.instances.push(this); } }
    vi.stubGlobal("BroadcastChannel", Channel); const session = create(); session.connect(); await session.login(credentials);
    expect(postMessage).toHaveBeenCalledWith("signed-in"); Channel.instances[0].onmessage?.({ data: "signed-out" });
    expect(session.getSnapshot()).toMatchObject({ status: "anonymous", user: null });
    expect(JSON.stringify(postMessage.mock.calls)).not.toContain(tokens.access_token); session.disconnect();
  });
});

it("renews and rechecks the profile near expiry during restoration", async () => {
 const clock = vi.spyOn(Date, "now").mockReturnValue(1000000); const session = create(); await session.login(credentials);
 expect(session.renewalDelay()).toBe(895000); clock.mockReturnValue(1896000); await session.restore();
 expect(calls("/refresh")).toHaveLength(1); expect(calls("/me")).toHaveLength(2);
});
it("rejects a stale protected response after logout without disclosing its data", async () => {
 const session = create(); await session.login(credentials); let release!: (response: Response) => void;
 fetchMock.mockImplementation(url => String(url).endsWith("/resource") ? new Promise(resolve => { release = resolve; }) : standard(url));
 const reading = session.get("/resource", z.unknown()); const rejected = expect(reading).rejects.toMatchObject({ status: 401 });
 await session.logout(); release(response({ private: "data" })); await rejected;
 expect(session.getSnapshot().status).toBe("anonymous");
});

it("GitHub connection mutations send bearer and fresh cookie-bound CSRF without retries",async()=>{
 const session=create();await session.login(credentials);const value=await session.post("/api/v1/auth/github/disconnect",z.object({value:z.string()}));expect(value.value).toBe("safe");
 const options=calls("/github/disconnect")[0][1]!;expect(options.method).toBe("POST");expect(new Headers(options.headers).get("X-CSRF-Token")).toBe(csrf);expect(new Headers(options.headers).get("Authorization")).toBe(`Bearer ${tokens.access_token}`);expect(calls("/github/disconnect")).toHaveLength(1);
});
it("GitHub revoked authorization does not revoke the CodeMate session",async()=>{
 const session=create();await session.login(credentials);fetchMock.mockImplementation(url=>String(url).includes("/github/")?Promise.resolve(response({detail:{code:"GITHUB_REAUTHORIZATION_REQUIRED",message:"Reconnect GitHub."}},424)):standard(url));
 await expect(session.get("/api/v1/github/repositories",z.object({value:z.string()}))).rejects.toMatchObject({status:424,code:"GITHUB_REAUTHORIZATION_REQUIRED"});expect(session.getSnapshot().status).toBe("authenticated");
});
it("GitHub mutations do not retry a failed state-changing request",async()=>{
 const session=create();await session.login(credentials);fetchMock.mockImplementation(url=>String(url).includes("/github/")?Promise.resolve(response({},503)):standard(url));await expect(session.post("/api/v1/auth/github/connect",z.object({value:z.string()}))).rejects.toMatchObject({status:503});expect(calls("/github/connect")).toHaveLength(1);expect(session.getSnapshot().status).toBe("authenticated");
});

it("sends AI input with bearer, custom header, cookie CSRF and no automatic mutation retry", async () => {
 const session = create(); await session.login(credentials);
 const body = { owner: "octocat", repo: "demo", installation_id: 10, workflow_run_id: 701 };
 await session.post("/api/v1/auth/ai/investigations", z.object({ value: z.string() }), body);
 const options = calls("/ai/investigations")[0][1]!;
 const headers = new Headers(options.headers);
 expect(headers.get("Authorization")).toBe(`Bearer ${tokens.access_token}`);
 expect(headers.get("X-CSRF-Token")).toBe(csrf);
 expect(headers.get("X-CodeMate-Request")).toBe("1");
 expect(JSON.parse(options.body as string)).toEqual(body);
 expect(options.credentials).toBe("include");
 fetchMock.mockImplementation(url => String(url).endsWith("/ai/investigations") ? Promise.resolve(response({ detail: { code: "AI_USER_BUSY", message: "Already running." } }, 409)) : standard(url));
 await expect(session.post("/api/v1/auth/ai/investigations", undefined, body)).rejects.toMatchObject({ code: "AI_USER_BUSY" });
 expect(calls("/ai/investigations")).toHaveLength(2);
});
