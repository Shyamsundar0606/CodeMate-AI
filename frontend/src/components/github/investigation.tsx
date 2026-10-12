"use client";
import Link from "next/link";
import { AnalyzeRun } from "@/components/ai/diagnostics";
import { useEffect, useRef, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import {
  useGitHub,
  pageSchema,
  runSchema,
  jobSchema,
  logSchema,
  repoPath,
  validRepo,
  validId,
  date,
} from "@/lib/github";
import {
  Heading,
  Loading,
  ErrorState,
  Pagination,
  External,
  Status,
} from "./shared";
export function LogViewer({ path }: { path: string }) {
  const [search, setSearch] = useState("");
  const [notice, setNotice] = useState("");
  const logs = useGitHub(path, logSchema);
  const viewer = useRef<HTMLElement>(null);
  useEffect(() => {
    viewer.current?.focus();
  }, [path]);
  const lines = (logs.data?.content || "")
    .split("\n")
    .map((text, index) => ({ text, number: index + 1 }))
    .filter((line) => line.text.toLowerCase().includes(search.toLowerCase()));
  async function copy() {
    if (
      !window.confirm(
        "Redaction is imperfect. Review this excerpt for secrets before copying or sharing. Copy the displayed lines?",
      )
    )
      return;
    try {
      await navigator.clipboard.writeText(
        lines
          .slice(0, 200)
          .map((l) => l.text)
          .join("\n"),
      );
      setNotice("Copied up to 200 displayed lines. Review before sharing.");
    } catch {
      setNotice(
        "Clipboard is unavailable. Select and review the text manually.",
      );
    }
  }
  return (
    <section
      id="selected-job-logs"
      ref={viewer}
      tabIndex={-1}
      aria-label="Job logs"
      className="card github-log"
    >
      <h3>Available job logs</h3>
      {logs.isPending ? (
        <p role="status" aria-live="polite">
          Loading job logs...
        </p>
      ) : logs.isError ? (
        <ErrorState error={logs.error} retry={() => void logs.refetch()} />
      ) : !logs.data?.content.trim() ? (
        <div role="status">
          <p>
            No log text is available yet. Logs may still be processing or may have expired.
          </p>
          <button
            type="button"
            className="button secondary"
            onClick={() => void logs.refetch()}
          >
            Try again
          </button>
        </div>
      ) : (
        <>
          <p>{logs.data?.warning}</p>
          {logs.data?.truncated && (
            <p role="status">Log truncated at the safe byte or line limit.</p>
          )}
          <div className="github-toolbar">
            <label>
              Search log
              <input
                type="search"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </label>
            <button className="button secondary" onClick={() => void copy()}>
              Copy displayed excerpt
            </button>
          </div>
          {notice && <p role="status">{notice}</p>}
          <pre aria-label="Job log content">
            {lines.map((line) => (
              <span className="log-line" key={line.number}>
                <span className="line-number" aria-hidden="true">
                  {line.number}
                </span>
                <span>{line.text || " "}</span>
                {"\n"}
              </span>
            ))}
          </pre>
          {!lines.length && <p>No matching log lines.</p>}
        </>
      )}
    </section>
  );
}
function Investigation({
  owner,
  repo,
  installation,
  runId,
}: {
  owner: string;
  repo: string;
  installation: string;
  runId: string;
}) {
  const [page, setPage] = useState(1);
  const [job, setJob] = useState<number | null>(null);
  const root = repoPath(owner, repo);
  const run = useGitHub(
    root + `/actions/runs/${runId}?installation_id=${installation}`,
    runSchema,
  );
  const jobs = useGitHub(
    root +
      `/actions/runs/${runId}/jobs?installation_id=${installation}&page=${page}`,
    pageSchema(jobSchema),
    run.isSuccess,
  );
  return (
    <>
      <Heading
        title={
          run.data
            ? `${run.data.name || "Workflow"} #${run.data.run_number}`
            : "Workflow run investigation"
        }
        description={`${owner}/${repo} · Run ID ${runId}`}
      />
      <Link
        href={`/dashboard/cicd?installation=${installation}&owner=${owner}&repo=${repo}`}
      >
        ← CI/CD monitoring
      </Link>
      {run.isPending ? (
        <Loading />
      ) : run.isError ? (
        <ErrorState error={run.error} />
      ) : (
        run.data && (
          <>
            <section className="card github-connection">
              <Status
                status={run.data.status}
                conclusion={run.data.conclusion}
              />
              <p>
                Event: {run.data.event} · Branch:{" "}
                {run.data.branch || "Unavailable"}
              </p>
              <p>
                Commit: <code>{run.data.sha}</code>
              </p>
              <p>
                Created: {date(run.data.created_at)} · Updated:{" "}
                {date(run.data.updated_at)}
              </p>
              <External url={run.data.html_url}>Open run on GitHub</External>
            </section>
            <AnalyzeRun context={{ installation_id: Number(installation), owner, repo, workflow_run_id: Number(runId) }} status={run.data.status} conclusion={run.data.conclusion} />
            <h2>Jobs and steps</h2>
            {jobs.isPending ? (
              <Loading />
            ) : jobs.isError ? (
              <ErrorState error={jobs.error} />
            ) : (
              <>
                <div className="github-list">
                  {jobs.data?.items.map((j) => (
                    <article
                      className={`card github-job ${j.conclusion === "failure" ? "failed-job" : ""}`}
                      key={j.id}
                    >
                      <div className="card-heading">
                        <h3>{j.name}</h3>
                        <Status status={j.status} conclusion={j.conclusion} />
                      </div>
                      <p>
                        {date(j.started_at)} → {date(j.completed_at)}
                      </p>
                      <ol className="github-steps">
                        {j.steps.map((s) => (
                          <li key={s.number}>
                            <span>{s.name}</span>
                            <Status
                              status={s.status}
                              conclusion={s.conclusion}
                            />
                          </li>
                        ))}
                      </ol>
                      <div className="github-toolbar">
                        <button
                          className="button secondary"
                          type="button"
                          aria-controls="selected-job-logs"
                          aria-expanded={job === j.id}
                          onClick={() => setJob(j.id)}
                        >
                          View logs for {j.name}
                        </button>
                        <External url={j.html_url}>Open job on GitHub</External>
                      </div>
                    </article>
                  ))}
                  {!jobs.data?.items.length && (
                    <p>No jobs available on this page.</p>
                  )}
                </div>
                <Pagination
                  page={page}
                  next={!!jobs.data?.has_next}
                  onPage={(p) => {
                    setPage(p);
                    setJob(null);
                  }}
                />
              </>
            )}
            {job && (
              <LogViewer
                key={job}
                path={
                  root +
                  `/actions/jobs/${job}/logs?installation_id=${installation}`
                }
              />
            )}
          </>
        )
      )}
      <p className="github-notice">
        Local AI suggestions are read-only; review evidence before changing code.
      </p>
    </>
  );
}
export function RunInvestigation() {
  const { runId } = useParams<{ runId: string }>();
  const p = useSearchParams();
  const owner = p.get("owner") || "";
  const repo = p.get("repo") || "";
  const installation = p.get("installation") || "";
  if (!validId(runId) || !validId(installation) || !validRepo(owner, repo))
    return (
      <>
        <Heading
          title="Invalid workflow context"
          description="Open a run from an authorized repository in CI/CD monitoring."
        />
        <Link href="/dashboard/cicd">Back to CI/CD</Link>
      </>
    );
  return (
    <Investigation
      key={`${installation}/${owner}/${repo}/${runId}`}
      {...{ owner, repo, installation, runId }}
    />
  );
}
