"use client";
import Link from "next/link";
import {
  useGitHub,
  connectionSchema,
  pageSchema,
  installationSchema,
  repositorySchema,
  runSchema,
  pullSchema,
  repoPath,
} from "@/lib/github";
function Counts({ installation }: { installation: number }) {
  const repos = useGitHub(
    `/api/v1/github/repositories?installation_id=${installation}`,
    pageSchema(repositorySchema),
  );
  const first = repos.data?.items[0];
  const root = first ? repoPath(first.owner, first.name) : "";
  const runs = useGitHub(
    root + `/actions/runs?installation_id=${installation}`,
    pageSchema(runSchema),
    !!first,
  );
  const pulls = useGitHub(
    root + `/pulls?installation_id=${installation}`,
    pageSchema(pullSchema),
    !!first,
  );
  const cards = [
    {
      title: "Connected repositories",
      value: repos.data?.total ?? "Unavailable",
      scope: `Installation ${installation} only`,
    },
    {
      title: "Recent workflow runs",
      value: runs.data?.items.length ?? "Unavailable",
      scope: "This run page",
    },
    {
      title: "Failed workflow runs",
      value:
        runs.data?.items.filter((r) => r.conclusion === "failure").length ??
        "Unavailable",
      scope: "This run page",
    },
    {
      title: "Open pull requests",
      value: pulls.data?.items.length ?? "Unavailable",
      scope: "This PR page",
    },
  ];
  return (
    <>
      <p className="muted">
        Preview scope: {first?.full_name || "first accessible repository"}.
        These are not account-wide activity totals.
      </p>
      <div className="metric-grid">
        {cards.map((c) => (
          <article className="card metric-card" key={c.title}>
            <h2>{c.title}</h2>
            <strong className="metric-state">{c.value}</strong>
            <p>{c.scope}</p>
          </article>
        ))}
      </div>
      {(repos.isError || runs.isError || pulls.isError) && (
        <p role="status">
          Some GitHub counts are unavailable. Open the relevant page to review
          permissions or rate limits.
        </p>
      )}
    </>
  );
}
export function GitHubOverview() {
  const conn = useGitHub("/api/v1/github/connection", connectionSchema);
  const installations = useGitHub(
    "/api/v1/github/installations?per_page=1",
    pageSchema(installationSchema),
    conn.data?.status === "connected",
  );
  return (
    <section aria-label="GitHub overview">
      {conn.data?.status === "connected" && installations.data?.items[0] ? (
        <Counts installation={installations.data.items[0].id} />
      ) : (
        <div className="card github-notice">
          <h2>Connected repositories</h2>
          <strong>
            {conn.isPending
              ? "Checking connection..."
              : conn.isError
                ? "Connection unavailable"
                : conn.data?.status === "connected"
                  ? "Installation preview unavailable"
                  : conn.data?.status === "reauthorization_required"
                    ? "Reconnect GitHub"
                    : "Not connected yet"}
          </strong>
          <p>
            {conn.isError
              ? "GitHub connection status is unavailable."
              : conn.data?.status === "connected"
                ? "No accessible installation preview is available."
                : "Connect GitHub to explore authorized repositories and CI/CD activity."}
          </p>
          <Link className="button primary" href="/dashboard/github">
            Review GitHub connection
          </Link>
        </div>
      )}
      <div className="github-toolbar">
        <Link href="/dashboard/repositories">Explore repositories →</Link>
        <Link href="/dashboard/cicd">Inspect CI/CD →</Link>
      </div>
    </section>
  );
}
