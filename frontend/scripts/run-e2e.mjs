import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";
import { createServer } from "node:net";
import { mkdir, rmdir } from "node:fs/promises";
const root = fileURLToPath(new URL("..", import.meta.url));
const python = resolve(root, "../backend/.venv/Scripts/python.exe");
const helper = resolve(root, "scripts/e2e_backend.py");
const prefix = `e2e_${randomBytes(5).toString("hex")}`;
const env = { ...process.env, CODEMATE_E2E: "1", NEXT_PUBLIC_API_URL: "http://localhost:8001", E2E_ACCOUNT_PREFIX: prefix, E2E_ACCOUNT_PASSWORD: `Test!Aa9${randomBytes(18).toString("hex")}` };
delete env.NO_COLOR; delete env.FORCE_COLOR;
const children = [];
let prepared = false; let lockOwned = false;
const lockPath = resolve(root, ".e2e-lock");
function run(executable, args, options = {}) {
  const result = spawnSync(executable, args, { cwd: root, env, stdio: "inherit", windowsHide: true, ...options });
  if (result.error || result.status !== 0) throw new Error("E2E command failed; see sanitized output above.");
}
function start(executable, args) {
  const child = spawn(executable, args, { cwd: root, env, stdio: "inherit", windowsHide: true }); children.push(child);
  child.on("error", () => console.error("Could not launch an E2E-owned server.")); return child;
}
async function free(port) {
  await new Promise((done, reject) => { const server = createServer(); server.once("error", () => reject(new Error(`Port ${port} is occupied. Stop its owner explicitly before E2E; this runner will not terminate it.`))); server.listen(port, "127.0.0.1", () => server.close(done)); });
}
async function waitFor(url, child) {
  for (let i = 0; i < 120; i++) {
    if (child.exitCode !== null) throw new Error("An E2E-owned server stopped before readiness.");
    try { const result = await fetch(url, { signal: AbortSignal.timeout(1500) }); if (result.ok) return; } catch { /* Bounded readiness polling. */ }
    await new Promise(done => setTimeout(done, 500));
  }
  throw new Error("E2E server readiness timed out.");
}
let cleaning;
async function cleanup() {
  if (cleaning) return cleaning;
  cleaning = (async () => {
    // Only our child PIDs are terminated. Development servers are never discovered or killed.
    for (const child of children.reverse()) {
      if (child.exitCode !== null) continue;
      const stopped = new Promise(done => child.once("exit", done)); child.kill();
      await Promise.race([stopped, new Promise(done => setTimeout(done, 3000))]);
    }
    try { if (prepared) run(python, [helper, "cleanup", prefix]); }
    finally { if (lockOwned) await rmdir(lockPath); }
  })(); return cleaning;
}
for (const signal of ["SIGINT", "SIGTERM"]) process.once(signal, () => void cleanup().finally(() => process.exit(1)));
try {
  await free(3000); await free(8001);
  await mkdir(lockPath); lockOwned = true;
  console.log("E2E uses only codemate_test_db / codemate_test_user. Do not run backend pytest concurrently.");
  run(python, [helper, "prepare", prefix]); prepared = true;
  run(process.execPath, [resolve(root, "node_modules/next/dist/bin/next"), "build"]);
  const backend = start(python, [helper, "serve", prefix]); await waitFor("http://127.0.0.1:8001/health/ready", backend);
  const frontend = start(process.execPath, [resolve(root, "node_modules/next/dist/bin/next"), "start", "--hostname", "127.0.0.1", "--port", "3000"]);
  await waitFor("http://127.0.0.1:3000", frontend);
  run(process.execPath, [resolve(root, "node_modules/@playwright/test/cli.js"), "test"]);
} catch (error) { console.error(error.message); process.exitCode = 1; }
finally { await cleanup(); }
