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
