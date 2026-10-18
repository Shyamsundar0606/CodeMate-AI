import { chromium, expect } from "@playwright/test";
import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { mkdir, rmdir } from "node:fs/promises";
import { createServer } from "node:net";
const root = fileURLToPath(new URL("..", import.meta.url));
const python = resolve(root, "../backend/.venv/Scripts/python.exe");
const helper = resolve(root, "scripts/automation_fixture.py");
const prefix = "e2e_" + randomBytes(5).toString("hex");
const children = []; let browser, page, locked = false, prepared = false;
const lock = resolve(root, ".e2e-lock");
const env = { ...process.env }; delete env.CODEMATE_REAL_VOICE;
function run(args) { const result = spawnSync(python, [helper, ...args, prefix], { cwd: root, env, stdio: "inherit", windowsHide: true }); if (result.status !== 0) throw Error("Guarded fixture preparation/cleanup failed."); }
function start(exe, args) { const child = spawn(exe, args, { cwd: root, env, stdio: "ignore", windowsHide: true }); children.push(child); return child; }
async function free(port) { await new Promise((done, reject) => { const server = createServer(); server.once("error", reject); server.listen(port, "127.0.0.1", () => server.close(done)); }); }
async function ready(url, child) { for (let i = 0; i < 100; i++) { if (child.exitCode !== null) throw Error("Fixture server stopped before readiness."); try { if ((await fetch(url, { signal: AbortSignal.timeout(1000) })).ok) return; } catch {} await new Promise(done => setTimeout(done, 300)); } throw Error("Fixture readiness timed out."); }
try {
  await free(8001); await free(3000); await mkdir(lock); locked = true;
  run(["prepare"]); prepared = true;
  const api = start(python, [helper, "serve", prefix]); await ready("http://127.0.0.1:8001/health/ready", api);
  const web = start(process.execPath, [resolve(root, "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", "3000"]); await ready("http://127.0.0.1:3000", web);
  browser = await chromium.launch({ channel: "msedge", headless: true });
  const context = await browser.newContext(); page = await context.newPage(); let errors = 0, executions = 0;
  page.on("pageerror", () => errors++); page.on("request", r => { if (r.url().endsWith("/execute")) executions++; });
  await page.route("http://localhost:8000/**", route => route.continue({ url: route.request().url().replace("localhost:8000", "localhost:8001") }));
  const name = prefix + "_user", password = "Test!Aa9" + randomBytes(18).toString("hex");
  await page.goto("http://localhost:3000/register"); await page.getByLabel("Username", { exact: true }).fill(name); await page.getByLabel("Email address").fill(name + "@example.com"); await page.getByLabel("Password", { exact: true }).fill(password); await page.getByLabel("Confirm password", { exact: true }).fill(password); await page.getByRole("button", { name: "Create account", exact: true }).click(); await page.waitForURL("**/login");
  await page.getByLabel("Email address").fill(name + "@example.com"); await page.getByLabel("Password", { exact: true }).fill(password); await page.getByRole("button", { name: "Sign in", exact: true }).click(); await page.waitForURL("**/dashboard");
  await page.route("https://github.com/login/oauth/authorize**", async route => { const source = new URL(route.request().url()), target = new URL("http://localhost:8001/api/v1/github/callback"); target.searchParams.set("state", source.searchParams.get("state")); target.searchParams.set("code", "fixture"); await route.fulfill({ status: 302, headers: { location: target.toString() }, body: "" }); });
  await page.goto("http://localhost:3000/dashboard/github"); await page.getByRole("button", { name: "Connect GitHub", exact: true }).click(); await expect(page.getByRole("heading", { name: "Connected as octocat" })).toBeVisible();
  await page.goto("http://localhost:3000/dashboard/automation"); await page.getByLabel("App installation").selectOption("10"); await page.getByRole("combobox", { name: /^Repository/ }).selectOption("octocat/secure-demo"); await page.getByLabel("Source paths").fill("main.py"); await page.getByRole("button", { name: "Inspect source", exact: true }).click(); await expect(page.getByRole("heading", { name: "Snapshot context" })).toBeVisible(); await expect(page.getByText("a".repeat(40), { exact: true })).toBeVisible();
  let generations = 0;
  page.on("request", r => { if (r.method() === "POST" && r.url().endsWith("/proposals")) generations++; });
  await page.getByLabel("Suggestion type").selectOption("explain"); await page.getByLabel("Developer request").fill("Explain main.py"); await page.getByRole("button", { name: "Generate suggestion", exact: true }).click(); await expect(page.getByRole("heading", { name: "Source explanation", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Reload session", exact: true }).click(); await expect(page.getByRole("heading", { name: "Source explanation", exact: true })).toBeVisible(); expect(generations).toBe(1);
  await page.getByLabel("Suggestion type").selectOption("patch");
  await page.getByLabel("Developer request").fill("Fix addition"); await page.getByRole("button", { name: "Generate suggestion", exact: true }).click(); await expect(page.getByLabel("Proposed unified diff")).toContainText("+    return a + b");
  await page.getByRole("button", { name: "Reject proposal", exact: true }).click(); await expect(page.getByText("rejected", { exact: true })).toBeVisible();
  await page.getByLabel("Developer request").fill("Propose addition after review"); await page.getByRole("button", { name: "Generate suggestion", exact: true }).click(); await page.getByRole("button", { name: "Review approval", exact: true }).click(); await expect(page.getByRole("dialog")).toBeVisible(); await page.getByRole("checkbox", { name: "python_tests" }).check(); await page.getByRole("button", { name: "Confirm review approval", exact: true }).dblclick(); await expect(page.getByText("approved", { exact: true })).toBeVisible(); await expect(page.getByRole("button", { name: "Apply patch and run validation (unavailable)", exact: true }).first()).toBeDisabled();
  // Respect the production six-mutation/minute budget when adding cancellation coverage.
  await new Promise(done => setTimeout(done, 61000));
  await page.getByLabel("Developer request").fill("Prepare a cancellable addition proposal"); await page.getByRole("button", { name: "Generate suggestion", exact: true }).click(); await page.getByRole("button", { name: "Cancel proposal", exact: true }).click(); await expect(page.getByText("cancelled", { exact: true })).toBeVisible();
  await page.reload(); await page.getByRole("button", { name: "octocat/secure-demo / aaaaaaaa" }).click(); await expect(page.getByText("approved", { exact: true })).toBeVisible(); await expect(page.getByText("cancelled", { exact: true })).toBeVisible();
  await page.getByLabel("App installation").selectOption("10"); await page.getByRole("combobox", { name: /^Repository/ }).selectOption("octocat/secure-demo");
  await page.getByLabel("Source paths").fill(".env"); await page.getByRole("button", { name: "Inspect source", exact: true }).click(); await expect(page.getByRole("alert")).toBeVisible();
  await page.goto("http://localhost:3000/dashboard/voice"); await page.getByRole("textbox").fill("CodeMate, propose a fix"); await page.getByRole("button", { name: "Send text command", exact: true }).click(); await expect(page.getByRole("link", { name: "Open relevant page" })).toHaveAttribute("href", "/dashboard/automation");
  await page.getByRole("link", { name: "Open relevant page" }).click(); await page.getByRole("button", { name: "octocat/secure-demo / aaaaaaaa" }).click();
  await mkdir(resolve(root, "test-results"), { recursive: true }); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: resolve(root, "test-results/automation-desktop.png"), fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 }); await page.getByRole("heading", { name: "Developer Automation", exact: true }).click(); await page.evaluate(() => window.scrollTo(0, 0)); await page.screenshot({ path: resolve(root, "test-results/automation-mobile.png"), fullPage: true });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth); expect(overflow).toBe(false); expect(errors).toBe(0); expect(executions).toBe(0);
  console.log(JSON.stringify({ browser: "Microsoft Edge", realFrontendAndFastAPI: true, disposableTestDatabase: true, upstreamGitHubAndOllama: "controlled fixtures", sourceInspection: true, diffPreview: true, rejection: true, reviewApproval: true, persistedHistory: true, secretPathRejected: true, voiceNavigation: true, executionRequests: executions, mobileOverflow: overflow, pageErrors: errors }));
} catch (error) {
  if (page?.url().includes("/dashboard/automation")) { await mkdir(resolve(root, "test-results"), { recursive: true }); await page.screenshot({ path: resolve(root, "test-results/automation-failure.png"), fullPage: true }); console.error("Automation fixture visible text:", (await page.locator("main").innerText()).slice(0, 1800)); }
  throw error;
} finally {
  await browser?.close();
  for (const child of children.reverse()) { if (child.exitCode !== null) continue; const stopped = new Promise(done => child.once("exit", done)); child.kill(); await Promise.race([stopped, new Promise(done => setTimeout(done, 3000))]); }
  if (prepared) run(["cleanup"]); if (locked) await rmdir(lock);
}
