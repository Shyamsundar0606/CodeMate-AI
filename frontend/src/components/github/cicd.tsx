"use client";
import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  useGitHub,
  pageSchema,
  repositorySchema,
  workflowSchema,
  runSchema,
  validId,
  validRepo,
  repoPath,
  date,
} from "@/lib/github";
import { InstallationPicker } from "./repositories";
import { Heading, Loading, ErrorState, Pagination, Runs } from "./shared";
function RepositoryPicker({
  installation,
  owner,
  repo,
  onChange,
}: {
  installation: string;
  owner: string;
  repo: string;
  onChange: (owner: string, repo: string) => void;
}) {
  const [page, setPage] = useState(1);
  const q = useGitHub(
    `/api/v1/github/repositories?installation_id=${installation}&page=${page}`,
    pageSchema(repositorySchema),
    validId(installation),
  );
  return (
    <div className="card github-picker">
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : (
        <>
          <label>
            Repository
            <select
              value={owner && repo ? `${owner}/${repo}` : ""}
              onChange={(e) => {
                const [o, r] = e.target.value.split("/");
                onChange(o || "", r || "");
              }}
            >
              <option value="">Choose a repository on this page</option>
              {q.data?.items.map((r) => (
                <option key={r.id} value={r.full_name}>
                  {r.full_name}
                </option>
              ))}
            </select>
          </label>
          <Pagination
            page={page}
            next={!!q.data?.has_next}
            onPage={(p) => {
              setPage(p);
              onChange("", "");
            }}
          />
        </>
      )}
    </div>
  );
}
function Monitor({
  owner,
  repo,
  installation,
}: {
  owner: string;
  repo: string;
  installation: string;
}) {
  const [page, setPage] = useState(1);
  const [workflowPage, setWorkflowPage] = useState(1);
  const [workflow, setWorkflow] = useState("");
  const [status, setStatus] = useState("");
  const root = repoPath(owner, repo);
  const workflows = useGitHub(
    root + `/workflows?installation_id=${installation}&page=${workflowPage}`,
    pageSchema(workflowSchema),
  );
  const runs = useGitHub(
    root +
      `/actions/runs?installation_id=${installation}&page=${page}${status ? `&status=${status}` : ""}${workflow ? `&workflow_id=${workflow}` : ""}`,
    pageSchema(runSchema),
  );
  const values = runs.data?.items || [];
  return (
    <>
      <div className="github-toolbar">
        <label>
          Workflow
          <select
            value={workflow}
            onChange={(e) => {
              setWorkflow(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All workflows</option>
            {workflows.data?.items.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Run status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            {["success", "failure", "in_progress", "cancelled", "queued"].map(
              (s) => (
                <option key={s} value={s}>
                  {s.replaceAll("_", " ")}
                </option>
              ),
            )}
          </select>
        </label>
        <button
          className="button secondary"
          disabled={runs.isFetching}
          onClick={() => {
            void runs.refetch();
            void workflows.refetch();
          }}
        >
          Refresh runs
        </button>
      </div>
      {workflows.isError && <ErrorState error={workflows.error} />}
      <Pagination
        page={workflowPage}
        next={!!workflows.data?.has_next}
        onPage={(p) => {
          setWorkflowPage(p);
          setWorkflow("");
          setPage(1);
        }}
      />
      <p className="muted">
        Workflow selector page {workflowPage}. Explicit refresh; no live push
        updates.
      </p>
      <div className="github-counts">
        {["success", "failure", "in_progress", "cancelled", "queued"].map(
          (s) => (
            <span key={s}>
              {s.replaceAll("_", " ")}:{" "}
              {runs.isSuccess
                ? values.filter((r) => r.conclusion === s || r.status === s)
                    .length
                : "unavailable"}
            </span>
          ),
        )}
      </div>
      <p>
        Counts describe this run page only. Fetched:{" "}
        {date(runs.data?.fetched_at || null)}
      </p>
      {runs.isPending ? (
        <Loading />
      ) : runs.isError ? (
        <ErrorState error={runs.error} />
      ) : (
        <>
          <Runs
            items={values}
            owner={owner}
            repo={repo}
            installation={installation}
          />
          <Pagination
            page={page}
            next={!!runs.data?.has_next}
            onPage={setPage}
          />
        </>
      )}
    </>
  );
}
export function CICDPage() {
  const p = useSearchParams();
  const router = useRouter();
  const installation = p.get("installation") || "";
  const owner = p.get("owner") || "";
  const repo = p.get("repo") || "";
  function select(i: string, o = "", r = "") {
    router.replace(
      `/dashboard/cicd?${new URLSearchParams({ installation: i, owner: o, repo: r })}`,
    );
  }
  return (
    <>
      <Heading
        title="CI/CD monitoring"
        description="Inspect GitHub Actions status, conclusions and jobs. Refresh explicitly for current data."
      />
      <InstallationPicker value={installation} onChange={(i) => select(i)} />
      {validId(installation) && (
        <RepositoryPicker
          key={installation}
          installation={installation}
          owner={owner}
          repo={repo}
          onChange={(o, r) => select(installation, o, r)}
        />
      )}{" "}
      {validId(installation) && validRepo(owner, repo) && (
        <Monitor
          key={`${installation}/${owner}/${repo}`}
          owner={owner}
          repo={repo}
          installation={installation}
        />
      )}
    </>
  );
}
