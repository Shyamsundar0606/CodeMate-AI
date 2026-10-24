import { test, expect, type Page } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { resolve } from "node:path";
const prefix = process.env.E2E_ACCOUNT_PREFIX;
const password = process.env.E2E_ACCOUNT_PASSWORD;
if (!prefix || !password || !/^e2e_[a-f0-9]{10}$/.test(prefix)) throw new Error("Use npm run test:e2e for an isolated test environment.");
const account = (suffix: string) => ({ username: `${prefix}_${suffix}`, email: `${prefix}_${suffix}@example.com` });
async function register(page: Page, suffix: string) {
 const data = account(suffix); await page.goto("/register"); if (suffix === "user") await page.screenshot({ path: "test-results/register-desktop.png", fullPage: true }); await page.getByLabel("Username", { exact: true }).fill(data.username); await page.getByLabel("Email address").fill(data.email); await page.getByLabel("Password", { exact: true }).fill(password!); await page.getByLabel("Confirm password", { exact: true }).fill(password!); await page.getByRole("button", { name: "Create account", exact: true }).click(); await expect(page).toHaveURL(/\/login$/); return data;
}
async function login(page: Page, email: string) { await page.getByLabel("Email address").fill(email); await page.getByLabel("Password", { exact: true }).fill(password!); await page.getByRole("button", { name: "Sign in", exact: true }).click(); await expect(page).toHaveURL(/\/dashboard$/); }
async function navigate(page: Page, label: string) { await page.getByRole("navigation", { name: "Workspace" }).getByRole("link", { name: label, exact: true }).click(); }
test("real registration, login, profile, reload, preferences and revoked logout", async ({ page, context }) => {
 const errors: string[] = []; page.on("pageerror", error => errors.push(error.message)); const data = await register(page, "user"); await login(page, data.email);
 await expect(page.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toBeVisible(); await expect(page.getByText("Online", { exact: true })).toHaveCount(2); await expect(page.getByText("Not connected yet")).toBeVisible(); await page.screenshot({ path: "test-results/dashboard-desktop.png", fullPage: true });
 const cookies = await context.cookies("http://localhost:8001/api/v1/auth/refresh"); const refreshCookie = cookies.find(cookie => cookie.name === "codemate_refresh"); expect(refreshCookie).toMatchObject({ httpOnly: true, path: "/api/v1/auth", sameSite: "Strict" });
 expect(await page.evaluate(() => ({ local: Object.keys(localStorage), session: Object.keys(sessionStorage) }))).toEqual({ local: [], session: [] });
 const originalCookie = refreshCookie!.value; await page.reload(); await expect(page.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toBeVisible(); const rotatedCookie = (await context.cookies("http://localhost:8001/api/v1/auth/refresh")).find(cookie => cookie.name === "codemate_refresh")!; expect(rotatedCookie.value === originalCookie).toBe(false);
 await navigate(page, "Profile"); await expect(page.getByRole("heading", { name: "Profile", exact: true })).toBeVisible(); await expect(page.locator("main").getByText(data.email, { exact: true })).toHaveCount(2); await expect(page.getByText("USER", { exact: true })).toBeVisible();
 await navigate(page, "Settings"); await page.getByLabel("Color theme").selectOption("light"); await page.getByLabel("Reduce motion").check(); await expect(page.locator("html")).toHaveAttribute("data-theme", "light"); await expect(page.locator("html")).toHaveAttribute("data-reduced-motion", "true");
 await page.reload(); await expect(page.getByLabel("Color theme")).toHaveValue("light");
 expect(await page.evaluate(() => Object.keys(localStorage))).toEqual(["codemate-preferences"]);
 await page.screenshot({ path: "test-results/settings-desktop.png", fullPage: true });
 await page.getByRole("button", { name: "Sign out", exact: true }).click(); await expect(page).toHaveURL(/\/login$/); await expect(page.getByText("Signed out. The server session was revoked.", { exact: true })).toBeVisible();
 expect((await context.cookies("http://localhost:8001/api/v1/auth/refresh")).some(cookie => cookie.name === "codemate_refresh")).toBe(false);
 await page.goto("/dashboard/profile"); await expect(page).toHaveURL(/\/login$/); await expect(page.getByRole("heading", { name: "Profile", exact: true })).toHaveCount(0); expect(errors).toEqual([]);
});
test("duplicate registration and invalid credentials use real backend errors", async ({ page }) => {
 const data = account("user"); await page.goto("/register"); await page.getByLabel("Username", { exact: true }).fill(data.username); await page.getByLabel("Email address").fill(data.email); await page.getByLabel("Password", { exact: true }).fill(password!); await page.getByLabel("Confirm password", { exact: true }).fill(password!); await page.getByRole("button", { name: "Create account", exact: true }).click(); await expect(page.locator("main").getByRole("alert")).toContainText("already registered");
 await page.goto("/login"); await page.getByLabel("Email address").fill(data.email); await page.getByLabel("Password", { exact: true }).fill("WrongPassword123!"); await page.getByRole("button", { name: "Sign in", exact: true }).click(); await expect(page.locator("main").getByRole("alert")).toContainText("incorrect"); await expect(page).toHaveURL(/\/login$/);
});
test("mobile keyboard navigation and cross-tab session invalidation", async ({ page, context }) => {
 await page.setViewportSize({ width: 390, height: 844 }); const data = await register(page, "mobile"); await login(page, data.email); await page.screenshot({ path: "test-results/dashboard-mobile.png", fullPage: true });
 expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
 await page.getByRole("button", { name: "Open navigation" }).click(); await expect(page.getByRole("dialog")).toBeVisible(); await page.keyboard.press("Tab"); expect(await page.evaluate(() => document.querySelector("dialog")?.contains(document.activeElement))).toBe(true); await page.keyboard.press("Escape"); await expect(page.getByRole("dialog")).not.toBeVisible();
 await page.getByRole("button", { name: "Open navigation" }).click(); await navigate(page, "Profile"); await expect(page.getByRole("heading", { name: "Profile", exact: true })).toBeVisible();
 const second = await context.newPage(); await second.goto("/dashboard"); await expect(second.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toBeVisible();
 await Promise.all([page.reload(), second.reload()]); await expect(page.getByRole("heading", { name: "Profile", exact: true })).toBeVisible(); await expect(second.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toBeVisible();
 await second.goto("/dashboard/settings"); await second.getByRole("button", { name: "Sign out", exact: true }).click(); await expect(second).toHaveURL(/\/login$/); await expect(page).toHaveURL(/\/login$/); await second.close();
});
test("administrator directory uses the backend role and enforces read-only access", async ({ page }) => {
 const data = await register(page, "admin"); execFileSync(resolve("../backend/.venv/Scripts/python.exe"), [resolve("scripts/e2e_backend.py"), "promote-test-admin", prefix!], { windowsHide: true });
 await login(page, data.email);
 const signIn = await page.request.post("http://localhost:8001/api/v1/auth/login", { headers: { "X-CodeMate-Request": "1", Origin: "http://localhost:3000" }, data: { email: data.email, password } });
 expect(signIn.status()).toBe(200);
 const adminToken = (await signIn.json()).access_token;
 const metrics = await page.request.get("http://localhost:8001/api/v1/operations/metrics", { headers: { Authorization: `Bearer ${adminToken}` } });
 expect(metrics.status()).toBe(200); expect(metrics.headers()["cache-control"]).toBe("no-store");
 expect((await metrics.json()).scope).toBe("process"); expect(await metrics.text()).not.toContain(data.email);
 await navigate(page, "User directory"); await expect(page.getByRole("heading", { name: "User directory", exact: true })).toBeVisible(); await expect(page.getByRole("cell", { name: data.username, exact: true })).toBeVisible(); await expect(page.getByRole("button", { name: "Previous" })).toBeDisabled(); await expect(page.getByRole("button", { name: /delete|promote|edit/i })).toHaveCount(0); await page.screenshot({ path: "test-results/admin-desktop.png", fullPage: true });
});

test("network outages hide protected content and local signout reports unconfirmed revocation", async ({ page }) => {
 const data = await register(page, "outage"); await login(page, data.email);
 await page.route("http://localhost:8001/**", route => route.abort("failed")); await page.reload();
 await expect(page.getByText("Could not verify your session")).toBeVisible(); await expect(page.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toHaveCount(0);
 await expect(page).toHaveURL(/\/dashboard$/); await page.unroute("http://localhost:8001/**"); await page.getByRole("button", { name: "Try again" }).click(); await expect(page.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toBeVisible();
 await navigate(page, "Settings"); await page.route("http://localhost:8001/**", route => route.abort("failed")); await page.getByRole("button", { name: "Sign out", exact: true }).click(); await expect(page).toHaveURL(/\/login$/); await expect(page.getByText("Signed out locally. Server revocation could not be confirmed; the cookie session may restore after reload.", { exact: true })).toBeVisible();
 await page.unroute("http://localhost:8001/**");
});


test("GitHub pages require a CodeMate session", async ({page}) => {
 for (const path of ["/dashboard/ai","/dashboard/ai/investigations/3c337168-8a43-4f3e-bbaf-cf055ec41101","/dashboard/github","/dashboard/repositories","/dashboard/cicd","/dashboard/cicd/runs/701?owner=octocat&repo=secure-demo&installation=10"]) {
  await page.goto(path);await expect(page).toHaveURL(/\/login$/);
 }
});

test("controlled GitHub authorization, repository activity, failed jobs, logs and disconnect", async ({page,context}) => {
 const errors:string[]=[];page.on("pageerror",error=>errors.push(error.message));
 await page.route("https://avatars.githubusercontent.com/**",route=>route.fulfill({status:200,contentType:"image/svg+xml",body:'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="#253146"/><text x="12" y="40" fill="#65ddd7" font-size="24">GH</text></svg>'}));
 const data=await register(page,"github");await login(page,data.email);await navigate(page,"GitHub");
 await expect(page.getByRole("heading",{name:"Connect your GitHub account"})).toBeVisible();
 // Browser authorization redirect only. Backend token exchange and REST requests use test-only HTTPX transport.
 await page.route("https://github.com/login/oauth/authorize**",async route=>{
  const url=new URL(route.request().url());expect(url.searchParams.get("code_challenge_method")).toBe("S256");
  const callback=new URL("http://localhost:8001/api/v1/github/callback");callback.searchParams.set("state",url.searchParams.get("state")!);callback.searchParams.set("code","fixture");
  await route.fulfill({status:302,headers:{location:callback.toString()},body:""});
 });
 await page.getByRole("button",{name:"Connect GitHub",exact:true}).click();await expect(page.getByRole("heading",{name:"Connected as octocat"})).toBeVisible();
 await page.getByRole("link",{name:"Explore repositories",exact:true}).click();await page.getByLabel("App installation").selectOption("10");await expect(page.getByRole("heading",{name:"octocat/secure-demo"})).toBeVisible();
 await page.screenshot({path:"test-results/github-repositories-desktop.png",fullPage:true});
 await page.getByLabel("Search this page").fill("secure");await expect(page.getByRole("heading",{name:"octocat/web-demo"})).toHaveCount(0);await page.getByRole("link",{name:"octocat/secure-demo",exact:true}).click();
 for(const [tab,text] of [["Branches","Protected"],["Commits","Fix session restoration"],["Pull Requests","Improve session checks"],["Issues","Refresh session edge case"]]){
  await page.getByRole("button",{name:tab,exact:true}).click();await expect(page.getByText(text,{exact:false}).first()).toBeVisible();
 }
 await page.getByRole("button",{name:"CI/CD",exact:true}).click();await page.getByRole("link",{name:"Backend Tests #128",exact:true}).click();
 await expect(page.getByText("Run API integration tests",{exact:true})).toBeVisible();await expect(page.locator(".failed-job")).toHaveCount(1);
 await page.getByRole("button",{name:"View logs for pytest"}).click();await expect(page.getByLabel("Job log content")).toContainText("AssertionError: expected 200, received 401");await expect(page.getByLabel("Job log content")).toContainText("<script>");expect(await page.locator("main script").count()).toBe(0);await expect(page.getByLabel("Job log content")).not.toContainText("ghu_");
 await page.getByLabel("Search log").fill("AssertionError");await expect(page.getByLabel("Job log content")).not.toContainText("<script>");await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:"test-results/github-investigation-desktop.png",fullPage:true});

 await page.getByRole("button",{name:"Analyze with AI",exact:true}).click();
 await expect(page).toHaveURL(/\/dashboard\/ai\/investigations\/[0-9a-f-]+$/);
 await expect(page.getByText(/Analysis: (queued|running)/)).toBeVisible();
 await expect(page.getByText(/Analysis: completed/)).toBeVisible({timeout:20000});
 await expect(page.getByRole("heading",{name:"Recorded job failure"})).toBeVisible();
 await page.getByRole("link",{name:/Open evidence E-/}).click();
 const evidence = page.locator("details.ai-evidence").filter({has:page.locator("summary",{hasText:"job_log"})}).first();
 await evidence.locator("summary").focus();await page.keyboard.press("Enter");await expect(evidence).toHaveAttribute("open","");
 await expect(evidence.locator("pre")).toContainText("AssertionError");
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:"test-results/ai-report-desktop.png",fullPage:true});
 await page.reload();await expect(page.getByRole("heading",{name:"Recorded job failure"})).toBeVisible();
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/ai-report-mobile.png",fullPage:true});await page.setViewportSize({width:1440,height:900});
 await page.getByRole("link",{name:"Investigation history",exact:true}).click();
 await expect(page.getByText(/Completed: 1/)).toBeVisible();
 await page.route("http://localhost:8001/api/v1/ai/status",route=>route.fulfill({status:200,contentType:"application/json",body:JSON.stringify({available:false,model_available:false,selected_model:"qwen2.5-coder:3b",message:"Ollama is unavailable; other features remain available."})}));
 await page.getByRole("button",{name:"Check local model"}).click();await expect(page.getByText("Ollama is unavailable; other features remain available.", { exact: true })).toBeVisible();
 await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
 await page.screenshot({path:"test-results/ai-history-mobile.png",fullPage:true});
 await page.setViewportSize({width:1440,height:900});await page.unroute("http://localhost:8001/api/v1/ai/status");
 await page.goto("/dashboard/cicd?installation=10&owner=octocat&repo=secure-demo");await expect(page.getByRole("link",{name:"Backend Tests #128"})).toBeVisible();await page.getByLabel("Run status").selectOption("success");await expect(page.getByRole("link",{name:"Backend Tests #127"})).toBeVisible();await expect(page.getByRole("link",{name:"Backend Tests #128"})).toHaveCount(0);
 await page.route("http://localhost:8001/api/v1/github/repositories?**",route=>route.fulfill({status:429,contentType:"application/json",body:JSON.stringify({detail:{code:"GITHUB_RATE_LIMITED",message:"GitHub rate limit reached. Wait before refreshing.",retry_after:30}})}));await page.goto("/dashboard/repositories?installation=10");await expect(page.locator("main").getByRole("alert")).toContainText("rate limit");await page.unroute("http://localhost:8001/api/v1/github/repositories?**");
 await page.setViewportSize({width:390,height:844});await page.getByRole("button",{name:"Open navigation"}).click();await navigate(page,"GitHub");await expect(page.getByRole("heading",{name:"Connected as octocat"})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);await page.screenshot({path:"test-results/github-connection-mobile.png",fullPage:true});
 await page.getByRole("button",{name:"Disconnect GitHub"}).click();await expect(page.getByRole("dialog",{name:"Disconnect GitHub?"})).toBeVisible();await page.getByRole("button",{name:"Confirm disconnect"}).click();await expect(page.getByRole("heading",{name:"Connect your GitHub account"})).toBeVisible();await expect(page.getByText("Disconnected. GitHub authorization was revoked.")).toBeVisible();
 expect(await page.evaluate(()=>({local:Object.keys(localStorage),session:Object.keys(sessionStorage)}))).toEqual({local:[],session:[]});expect((await context.cookies()).some(c=>c.name.includes("github_state"))).toBe(false);expect(errors).toEqual([]);
});


test("missing refresh cookie restoration and operational metrics enforce real API authorization", async ({ page, context }) => {
 const data = await register(page, "voice"); await login(page, data.email);
 const apiLogin = await context.request.post("http://localhost:8001/api/v1/auth/login", { headers: { "X-CodeMate-Request": "1", Origin: "http://localhost:3000" }, data: { email: data.email, password } });
 expect(apiLogin.status()).toBe(200);
 const token = (await apiLogin.json()).access_token;
 expect((await context.request.get("http://localhost:8001/api/v1/operations/metrics")).status()).toBe(401);
 expect((await context.request.get("http://localhost:8001/api/v1/operations/metrics", { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(403);
 await context.clearCookies(); await page.reload(); await expect(page).toHaveURL(/\/login$/);
 await expect(page.getByRole("heading", { name: `Welcome back, ${data.username}.` })).toHaveCount(0);
});
