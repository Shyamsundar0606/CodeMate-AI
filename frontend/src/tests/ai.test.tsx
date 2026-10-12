import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AIOverview, AnalyzeRun, InvestigationReport } from "@/components/ai/diagnostics";
import { investigationSchema } from "@/lib/ai";
import { ApiError } from "@/lib/api/client";
import { user } from "./fixtures";
const { get, post, push, state } = vi.hoisted(() => ({
  get: vi.fn(), post: vi.fn(), push: vi.fn(), state: { status: "authenticated" },
}));
const id = "3c337168-8a43-4f3e-bbaf-cf055ec41101";
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }), useParams: () => ({ id: "3c337168-8a43-4f3e-bbaf-cf055ec41101" }) }));
vi.mock("@/providers/auth-provider", () => ({ useAuth: () => ({ user, status: state.status, session: { get, post } }) }));
const context = { owner: "octocat", repo: "secure-demo", installation_id: 10, workflow_run_id: 701 };
const ready = { available: true, model_available: true, selected_model: "qwen2.5-coder:3b", message: "Local model ready." };
const report = {
  summary: "A failed assertion was observed.", failure_category: "python_test",
  workflow_name: "Backend Tests", commit_sha: "a".repeat(40), branch: "main", run_conclusion: "failure",
  analyzed_job_ids: [801], model_name: "qwen2.5-coder:3b", evidence_completeness: "partial",
  recommended_actions: ["Review the failure."], limitations: ["Root cause remains uncertain."],
  findings: [{ id: "F1", title: "Assertion failure", description: "An assertion failed.",
    severity: "MEDIUM", confidence: "LOW", root_cause_hypothesis: "The expected value may be incorrect.",
    suggested_fix: "Review the expected value.", verification_steps: ["Rerun pytest."],
    evidence: [{ evidence_id: "E1", quote: "AssertionError: expected 200" }] }],
  evidence: [{ id: "E1", workflow_run_id: 701, job_id: 801, step: "pytest", source: "job_log",
    excerpt: "AssertionError: expected 200\n<script>alert(1)</script>", line_start: 1, line_end: 2,
    timestamp: null, redacted: true, truncated: true }],
};
const item = {
  id, ...context, status: "completed", stage: "completed", attempts: 1, max_attempts: 3,
  created_at: "2026-10-12T12:00:00Z", started_at: "2026-10-12T12:00:01Z",
  completed_at: "2026-10-12T12:00:02Z", error_code: null, error_message: null, report,
};
const history = { items: [item], page: 1, has_next: false, completed_count: 1, failed_count: 0 };
function mount(element: React.ReactNode) {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })}>{element}</QueryClientProvider>);
}
beforeEach(() => {
  state.status = "authenticated"; push.mockReset(); post.mockReset().mockResolvedValue(item);
  get.mockReset().mockImplementation((path: string) => Promise.resolve(path.includes("/status") ? ready :
    path.includes("?page=") ? history : item));
});
it("renders connected local model and real history counts", async () => {
  mount(<AIOverview />);
  expect(await screen.findByText("Selected model: qwen2.5-coder:3b")).toBeVisible();
  expect(await screen.findByText(/Completed: 1/)).toBeVisible();
  expect(screen.getByRole("link", { name: /octocat\/secure-demo/ })).toHaveAttribute("href", "/dashboard/ai/investigations/" + id);
});
it("explains unavailable Ollama without breaking history", async () => {
  get.mockImplementation((path: string) => Promise.resolve(path.includes("/status")
    ? { ...ready, available: false, model_available: false, message: "Ollama is unavailable." } : history));
  mount(<AIOverview />);
  expect(await screen.findByText("Ollama is unavailable.")).toBeVisible();
  expect(await screen.findByText(/Completed: 1/)).toBeVisible();
});
it("starts diagnosis only after a click using the protected backend", async () => {
  mount(<AnalyzeRun context={context} status="completed" conclusion="failure" />);
  const button = await screen.findByRole("button", { name: "Analyze with AI" });
  await waitFor(() => expect(button).toBeEnabled());
  expect(post).not.toHaveBeenCalled();
  await userEvent.click(button);
  expect(post).toHaveBeenCalledWith("/api/v1/auth/ai/investigations", investigationSchema, context);
  expect(push).toHaveBeenCalledWith("/dashboard/ai/investigations/" + id);
});
it("blocks duplicate submissions while start is pending", async () => {
  post.mockImplementation(() => new Promise(() => {}));
  mount(<AnalyzeRun context={context} status="completed" conclusion="failure" />);
  const button = await screen.findByRole("button", { name: "Analyze with AI" });
  await waitFor(() => expect(button).toBeEnabled());
  await userEvent.click(button);
  expect(screen.getByRole("button", { name: "Starting investigation..." })).toBeDisabled();
  expect(post).toHaveBeenCalledTimes(1);
});
it("does not diagnose a successful run", () => {
  mount(<AnalyzeRun context={context} status="completed" conclusion="success" />);
  expect(screen.getByText("No failure detected")).toBeVisible();
  expect(screen.queryByRole("button", { name: "Analyze with AI" })).toBeNull();
  expect(post).not.toHaveBeenCalled();
});
it("explains unsupported in-progress runs", () => {
  mount(<AnalyzeRun context={context} status="in_progress" conclusion={null} />);
  expect(screen.getByText(/after the workflow run completes/)).toBeVisible();
  expect(post).not.toHaveBeenCalled();
});
it.each(["queued", "running"])("shows persisted %s progress and cancellation", async status => {
  get.mockResolvedValue({ ...item, status, stage: "local_diagnosis", report: null });
  mount(<InvestigationReport />);
  expect(await screen.findByText(new RegExp("Analysis: " + status))).toBeVisible();
  expect(screen.getByRole("button", { name: "Cancel investigation" })).toBeEnabled();
});
it("renders validated report and inert evidence with keyboard controls", async () => {
  mount(<InvestigationReport />);
  expect(await screen.findByText("Assertion failure")).toBeVisible();
  expect(screen.getByText("Severity: MEDIUM | Confidence: LOW")).toBeVisible();
  const link = screen.getByRole("link", { name: "Open evidence E1" });
  expect(link).toHaveAttribute("href", "#evidence-E1");
  const summary = screen.getByText(/E1.*job_log/, { selector: "summary" });
  summary.focus(); expect(summary).toHaveFocus(); await userEvent.click(summary);
  expect(summary.closest("details")).toHaveAttribute("open");
  expect(screen.getByText(/<script>alert/)).toBeVisible();
  expect(document.querySelector("main script")).toBeNull();
  expect(screen.getByText("Redacted: yes | Truncated: yes")).toBeVisible();
});
it("shows missing evidence honestly", async () => {
  get.mockResolvedValue({ ...item, report: { ...report, findings: [], evidence: [], evidence_completeness: "missing" } });
  mount(<InvestigationReport />);
  expect(await screen.findByText(/No log evidence was collected/)).toBeVisible();
  expect(screen.queryByText("Assertion failure")).toBeNull();
});
it("retries supported failed analyses via the backend", async () => {
  get.mockResolvedValue({ ...item, status: "failed", error_code: "AI_TIMEOUT", error_message: "Local model timed out.", report: null });
  mount(<InvestigationReport />);
  expect(await screen.findByRole("alert")).toHaveTextContent("timed out");
  await userEvent.click(screen.getByRole("button", { name: "Retry investigation" }));
  expect(post).toHaveBeenCalledWith("/api/v1/auth/ai/investigations/" + id + "/retry", investigationSchema);
});
it("hides retry after the attempt budget", async () => {
  get.mockResolvedValue({ ...item, status: "failed", attempts: 3, report: null });
  mount(<InvestigationReport />);
  await screen.findByText(/Analysis: failed/);
  expect(screen.queryByRole("button", { name: "Retry investigation" })).toBeNull();
});
it.each([401, 403, 404])("shows safe %s errors", async status => {
  get.mockRejectedValue(new ApiError("Access unavailable.", status));
  mount(<InvestigationReport />);
  expect(await screen.findByRole("alert")).toHaveTextContent("Access unavailable.");
});
it("paginates history with authenticated requests", async () => {
  get.mockImplementation((path: string) => Promise.resolve(path.includes("/status") ? ready : { ...history, has_next: true }));
  mount(<AIOverview />);
  await screen.findByText(/Completed: 1/);
  await userEvent.click(screen.getByRole("button", { name: "Next page" }));
  await waitFor(() => expect(get.mock.calls.some(([path]) => path.endsWith("?page=2"))).toBe(true));
});
it("avoids requests after session expiration and never targets Ollama", () => {
  state.status = "anonymous"; mount(<AIOverview />);
  expect(get).not.toHaveBeenCalled();
  expect(post).not.toHaveBeenCalled();
});
it("validates structured report fields instead of accepting arbitrary output", () => {
  expect(investigationSchema.safeParse(item).success).toBe(true);
  expect(investigationSchema.safeParse({ ...item, report: { ...report, findings: [{}] } }).success).toBe(false);
});
