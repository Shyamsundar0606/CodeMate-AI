import { defineConfig } from "@playwright/test";
export default defineConfig({ testDir: "./e2e", fullyParallel: false, workers: 1, retries: 0, timeout: 45000, reporter: "list", use: { baseURL: "http://localhost:3000", browserName: "chromium", channel: "msedge", trace: "off", video: "off", screenshot: "only-on-failure" }, outputDir: "test-results" });
