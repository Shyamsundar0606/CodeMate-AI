"use client";
import Link from "next/link";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import { githubUrl, runLabel, type Run } from "@/lib/github";
export function Heading({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">GITHUB · READ ONLY</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
    </div>
  );
}
export function ErrorState({
  error,
  retry,
}: {
  error: unknown;
  retry?: () => void;
}) {
  return (
    <div className="card github-notice" role="alert">
      <p>{apiErrorMessage(error)}</p>
      {error instanceof ApiError && error.retryAfter && (
        <p>Wait at least {error.retryAfter} seconds before refreshing.</p>
      )}
      <Link href="/dashboard/github">Review GitHub connection</Link>
      {retry && !(error instanceof ApiError && error.status === 429) && (
        <button className="button secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function Loading() {
  return (
    <div className="card github-notice" role="status" aria-live="polite">
      <span>Loading authorized GitHub data...</span>
      <div className="github-skeleton" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </div>
  );
}
export function External({
  url,
  children,
}: {
  url: string;
  children: React.ReactNode;
}) {
  return (
    <a href={githubUrl(url)} target="_blank" rel="noopener noreferrer">
      {children} ↗
    </a>
  );
}
export function Pagination({
  page,
  next,
  onPage,
}: {
  page: number;
  next: boolean;
  onPage: (page: number) => void;
}) {
  return (
    <div className="github-pagination">
      <button
        className="button secondary"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
      >
        Previous page
      </button>
      <span>Page {page}</span>
      <button
        className="button secondary"
        disabled={!next || page >= 1000}
        onClick={() => onPage(page + 1)}
      >
        Next page
      </button>
    </div>
  );
}
export function Status({
  status,
  conclusion,
}: {
  status: string;
  conclusion: string | null;
}) {
  return (
    <span
      className={`badge run-status ${conclusion === "failure" || conclusion === "timed_out" ? "failed" : conclusion === "success" ? "successful" : ""}`}
    >
      {runLabel(status, conclusion)}
    </span>
  );
}
export function Runs({
  items,
  owner,
  repo,
  installation,
}: {
  items: Run[];
  owner: string;
  repo: string;
  installation: string;
}) {
  return (
    <div className="github-list">
      {items.length === 0 && <p>No workflow runs on this page.</p>}
      {items.map((run) => (
        <article className="card github-row" key={run.id}>
          <div>
            <Link
              href={`/dashboard/cicd/runs/${run.id}?owner=${encodeURIComponent(owner)}&repo=${encodeURIComponent(repo)}&installation=${installation}`}
            >
              <strong>
                {run.name || "Workflow"} #{run.run_number}
              </strong>
            </Link>
            <p>
              {run.branch || "No branch"} · {run.sha.slice(0, 7)} · {run.event}
            </p>
            <p>
              {run.duration_seconds === null
                ? "Duration unavailable"
                : `${run.duration_seconds}s`}{" "}
              · Updated {new Date(run.updated_at).toLocaleString()}
            </p>
          </div>
          <Status status={run.status} conclusion={run.conclusion} />
        </article>
      ))}
    </div>
  );
}
