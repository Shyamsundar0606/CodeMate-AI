import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { GitHubConnectionPage } from "@/components/github/connection";
import { RepositoryExplorer } from "@/components/github/repositories";
import { RepositoryDetail } from "@/components/github/detail";
import { CICDPage } from "@/components/github/cicd";
import { RunInvestigation, LogViewer } from "@/components/github/investigation";
import { ApiError } from "@/lib/api/client";
import { authorizationUrl, validRepo, validId, runLabel } from "@/lib/github";
import { user } from "./fixtures";
const { get, post, replace, state } = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  replace: vi.fn(),
  state: {
    query: "",
    status: "authenticated",
    params: { owner: "octocat", repo: "secure-demo", runId: "701" },
  },
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(state.query),
  useParams: () => state.params,
  useRouter: () => ({ replace }),
}));
vi.mock("@/providers/auth-provider", () => ({
  useAuth: () => ({ user, status: state.status, session: { get, post } }),
}));
const date = "2026-10-01T10:00:00Z";
const connection = {
  configured: true,
  status: "connected",
  github_login: "octocat",
  github_display_name: "Fixture account",
  github_avatar_url: null,
  granted_permissions: { contents: "read" },
  last_verified_at: date,
  install_url: null,
};
const repo = {
  id: 42,
  name: "secure-demo",
  full_name: "octocat/secure-demo",
  owner: "octocat",
  description: "Controlled fixture",
  private: true,
  default_branch: "main",
  language: "Python",
  stars: 7,
  forks: 2,
  fork: false,
  updated_at: date,
  pushed_at: date,
  html_url: "https://github.com/octocat/secure-demo",
};
const run = {
  id: 701,
  name: "Backend Tests",
  run_number: 128,
  branch: "main",
  sha: "a".repeat(40),
  event: "push",
  status: "completed",
  conclusion: "failure",
  created_at: date,
  updated_at: date,
  started_at: date,
  duration_seconds: 120,
  html_url: "https://github.com/octocat/secure-demo/actions/runs/701",
};
const page = (items: unknown[], next = false) => ({
  items,
  page: 1,
  per_page: 20,
  has_next: next,
  total: items.length,
  scope: "Selected repository",
  fetched_at: date,
});
function fixture(path: string): unknown {
  if (path.includes("/connection")) return connection;
  if (path.includes("/installations"))
    return page([
      {
        id: 10,
        account: "octocat",
        repository_selection: "selected",
        permissions: { contents: "read" },
        suspended: false,
      },
    ]);
  if (path.includes("/logs"))
    return {
      job_id: 801,
      content:
        "AssertionError: expected 200, received 401\n<script>alert('unsafe')</script>\nsecret=[REDACTED]",
      byte_limit: 262144,
      truncated: false,
      redacted: true,
      warning: "Redaction is imperfect. Review before sharing.",
      fetched_at: date,
    };
  if (path.includes("/jobs"))
    return page([
      {
        id: 801,
        run_id: 701,
        name: "pytest",
        status: "completed",
        conclusion: "failure",
        started_at: date,
        completed_at: date,
        html_url: run.html_url,
        steps: [
          {
            number: 1,
            name: "Run API integration tests",
            status: "completed",
            conclusion: "failure",
          },
        ],
      },
    ]);
  if (path.includes("/actions/runs/701")) return run;
  if (path.includes("/actions/runs")) return page([run]);
  if (path.includes("/workflows"))
    return page([
      {
        id: 11,
        name: "Backend Tests",
        path: "tests.yml",
        state: "active",
        html_url: run.html_url,
      },
    ]);
  if (path.includes("/branches"))
    return page([{ name: "main", sha: "a".repeat(40), protected: true }]);
  if (path.includes("/commits"))
    return page([
      {
        sha: "a".repeat(40),
        short_sha: "aaaaaaa",
        message: "Fix session checks",
        author: null,
        timestamp: date,
        html_url: repo.html_url,
      },
    ]);
  if (path.includes("/pulls"))
    return page([
      {
        number: 4,
        title: "Improve session checks",
        state: "open",
        author: "octocat",
        created_at: date,
        updated_at: date,
        base: "main",
        head: "fix-session",
        draft: false,
        html_url: repo.html_url,
      },
    ]);
  if (path.includes("/issues"))
    return page([
      {
        number: 5,
        title: "Refresh edge case",
        state: "open",
        author: "octocat",
        created_at: date,
        updated_at: date,
        labels: ["bug"],
        html_url: repo.html_url,
      },
    ]);
  if (path.includes("/repositories?")) return page([repo]);
  return repo;
}
function mount(element: React.ReactNode) {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({
          defaultOptions: { queries: { retry: false, gcTime: 0 } },
        })
      }
    >
      {element}
    </QueryClientProvider>,
  );
}
beforeEach(() => {
  state.query = "installation=10";
  state.status = "authenticated";
  state.params = { owner: "octocat", repo: "secure-demo", runId: "701" };
  get
    .mockReset()
    .mockImplementation((path: string) => Promise.resolve(fixture(path)));
  post.mockReset();
  replace.mockReset();
});
it("shows disconnected setup without a connect request", async () => {
  get.mockResolvedValue({
    ...connection,
    configured: false,
    status: "disconnected",
  });
  mount(<GitHubConnectionPage />);
  expect(
    await screen.findByText("GitHub integration not configured"),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Connect GitHub" })).toBeDisabled();
  expect(post).not.toHaveBeenCalled();
});
it("shows connected account metadata without credentials", async () => {
  mount(<GitHubConnectionPage />);
  expect(
    await screen.findByRole("heading", { name: "Connected as octocat" }),
  ).toBeVisible();
  expect(document.body.textContent).not.toMatch(
    /ghu_|ghr_|encrypted_access_token/,
  );
});
it("displays cancelled callback and removes the query from navigation", async () => {
  state.query = "github_result=github_authorization_cancelled";
  mount(<GitHubConnectionPage />);
  expect(screen.getByText("GitHub authorization was cancelled.")).toBeVisible();
  await waitFor(() =>
    expect(replace).toHaveBeenCalledWith("/dashboard/github"),
  );
});
it("requires confirmation before disconnect and reports remote revocation honestly", async () => {
  post.mockResolvedValue({
    disconnected: true,
    remote_revoked: false,
    message: "Disconnected locally. Remote revocation was not confirmed.",
  });
  mount(<GitHubConnectionPage />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Disconnect GitHub" }),
  );
  expect(post).not.toHaveBeenCalled();
  expect(screen.getByRole("dialog")).toBeVisible();
  await userEvent.click(
    screen.getByRole("button", { name: "Confirm disconnect" }),
  );
  expect(await screen.findByText(/Disconnected locally/)).toBeVisible();
  expect(post).toHaveBeenCalledWith(
    "/api/v1/auth/github/disconnect",
    expect.anything(),
  );
});
it("reports failed disconnect without claiming success", async () => {
  post.mockRejectedValue(new ApiError("Database unavailable", 503));
  mount(<GitHubConnectionPage />);
  await userEvent.click(
    await screen.findByRole("button", { name: "Disconnect GitHub" }),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Confirm disconnect" }),
  );
  expect(await screen.findByText("Database unavailable")).toBeVisible();
  expect(screen.getByRole("dialog")).toBeVisible();
});
it("renders authorized private repository data and page scope", async () => {
  mount(<RepositoryExplorer />);
  expect(
    await screen.findByRole("heading", { name: "octocat/secure-demo" }),
  ).toBeVisible();
  expect(screen.getByText("Private")).toBeVisible();
  expect(screen.getByText(/not an account-wide total/)).toBeVisible();
});
it("sends search and sorting within authorized pagination", async () => {
  mount(<RepositoryExplorer />);
  await screen.findByText("Controlled fixture");
  await userEvent.type(screen.getByLabelText("Search this page"), "secure");
  await userEvent.selectOptions(
    screen.getByLabelText("Sort this page"),
    "stars",
  );
  await waitFor(() =>
    expect(get).toHaveBeenCalledWith(
      expect.stringContaining("q=secure&sort=stars"),
      expect.anything(),
    ),
  );
});
it("loads another repository page when GitHub has a next page", async () => {
  get.mockImplementation((p: string) =>
    Promise.resolve(
      p.includes("/repositories?") ? page([repo], true) : fixture(p),
    ),
  );
  mount(<RepositoryExplorer />);
  await screen.findByText("Controlled fixture");
  await userEvent.click(
    screen.getAllByRole("button", { name: "Next page" })[1],
  );
  await waitFor(() =>
    expect(get).toHaveBeenCalledWith(
      expect.stringContaining("installation_id=10&page=2"),
      expect.anything(),
    ),
  );
});
it("handles repository empty states", async () => {
  get.mockImplementation((p: string) =>
    Promise.resolve(p.includes("/repositories?") ? page([]) : fixture(p)),
  );
  mount(<RepositoryExplorer />);
  expect(await screen.findByText(/No repositories match/)).toBeVisible();
});
it("shows safe rate-limit information without an automatic retry", async () => {
  get.mockRejectedValue(
    new ApiError(
      "GitHub rate limit reached",
      429,
      "http",
      "GITHUB_RATE_LIMITED",
      30,
    ),
  );
  mount(<RepositoryExplorer />);
  expect((await screen.findAllByRole("alert"))[0]).toHaveTextContent(
    "Wait at least 30 seconds",
  );
  expect(
    screen.queryByRole("button", { name: "Try again" }),
  ).not.toBeInTheDocument();
});
it("renders repository overview", async () => {
  mount(<RepositoryDetail />);
  expect(await screen.findByText("Default branch: main")).toBeVisible();
});
it("renders branches", async () => {
  state.query += "&tab=Branches";
  mount(<RepositoryDetail />);
  expect(await screen.findByText("Protected")).toBeVisible();
});
it("handles missing commit author", async () => {
  state.query += "&tab=Commits";
  mount(<RepositoryDetail />);
  expect(await screen.findByText(/Author unavailable/)).toBeVisible();
});
it("renders pull request branches", async () => {
  state.query += "&tab=Pull+Requests";
  mount(<RepositoryDetail />);
  expect(await screen.findByText(/fix-session/)).toBeVisible();
});
it("renders issues distinctly", async () => {
  state.query += "&tab=Issues";
  mount(<RepositoryDetail />);
  expect(
    await screen.findByRole("link", { name: "#5 Refresh edge case ↗" }),
  ).toBeVisible();
  expect(screen.queryByText(/Improve session checks/)).not.toBeInTheDocument();
});
it("rejects invalid repository context before requesting data", () => {
  state.params.owner = "https:evil";
  mount(<RepositoryDetail />);
  expect(screen.getByText("Invalid repository context")).toBeVisible();
  expect(get).not.toHaveBeenCalled();
});
it("interprets a completed failed run as failure", async () => {
  state.query += "&owner=octocat&repo=secure-demo";
  mount(<CICDPage />);
  expect(await screen.findByText(/120s · Updated/)).toBeVisible();
  expect(
    screen.getByText("failure", { selector: "span.run-status" }),
  ).toBeVisible();
});
it("highlights failed jobs and steps and fetches logs only after a click", async () => {
  state.query += "&owner=octocat&repo=secure-demo";
  mount(<RunInvestigation />);
  expect(await screen.findByText("Run API integration tests")).toBeVisible();
  expect(screen.getByText("pytest").closest("article")).toHaveClass(
    "failed-job",
  );
  expect(get.mock.calls.some(([p]) => p.includes("/logs"))).toBe(false);
  await userEvent.click(
    screen.getByRole("button", { name: "View logs for pytest" }),
  );
  expect(await screen.findByLabelText("Job log content")).toHaveTextContent(
    "AssertionError",
  );
});
it("renders log text without HTML execution and supports search", async () => {
  mount(<LogViewer path="/api/v1/github/fixture/logs" />);
  const log = await screen.findByLabelText("Job log content");
  expect(log).toHaveTextContent("<script>");
  expect(log.querySelector("script")).toBeNull();
  await userEvent.type(screen.getByLabelText("Search log"), "AssertionError");
  expect(log).toHaveTextContent("AssertionError");
  expect(log).not.toHaveTextContent("<script>");
});
it("does not request GitHub data after session expiration", () => {
  state.status = "anonymous";
  mount(<GitHubConnectionPage />);
  expect(get).not.toHaveBeenCalled();
});
it("validates routes and authorization destinations", () => {
  expect(validRepo("octocat", "secure-demo")).toBe(true);
  expect(validRepo("octocat", "..")).toBe(false);
  expect(validId("701")).toBe(true);
  expect(validId("-1")).toBe(false);
  expect(() =>
    authorizationUrl("https://evil.example/login/oauth/authorize"),
  ).toThrow();
  expect(runLabel("completed", "failure")).toBe("failure");
  expect(runLabel("in_progress", null)).toBe("in progress");
});
