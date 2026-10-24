import { afterEach, expect, it, vi } from "vitest";

afterEach(() => { vi.unstubAllEnvs(); vi.resetModules(); });

it.each([["", ".next"], ["1", ".next-e2e"]])("keeps %s build output and bypasses stale persisted workers", async (value, directory) => {
  vi.stubEnv("CODEMATE_E2E", value);
  const { default: config } = await import("../../next.config");
  expect(config.distDir).toBe(directory);
  expect(config.experimental?.turbopackFileSystemCacheForBuild).toBe(false);
  expect(config.experimental?.turbopackFileSystemCacheForDev).toBeUndefined();
  expect(config.reactStrictMode).toBe(true);
});

it("sets a production-compatible baseline CSP without eval and protects framing", async () => {
  vi.stubEnv("NODE_ENV", "production");
  vi.stubEnv("NEXT_PUBLIC_API_URL", "https://api.codemate.example");
  const { default: config } = await import("../../next.config");
  const rules = await config.headers!();
  const headers = Object.fromEntries(rules[0].headers.map(item => [item.key, item.value]));
  expect(config.poweredByHeader).toBe(false);
  expect(headers["Content-Security-Policy"]).toContain("https://api.codemate.example");
  expect(headers["Content-Security-Policy"]).not.toContain("unsafe-eval");
  expect(headers["Content-Security-Policy"]).toContain("frame-ancestors 'none'");
  expect(headers["Permissions-Policy"]).toContain("microphone=(self)");
  expect(headers["X-Content-Type-Options"]).toBe("nosniff");
});

it("rejects credential-bearing origins in security headers", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_URL", "https://user:private@api.example");
  const { default: config } = await import("../../next.config");
  await expect(config.headers!()).rejects.toThrow("Public API origin is invalid");
});
