"use client";
import Link from "next/link";
import { useState } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import {
  useGitHub,
  pageSchema,
  repositorySchema,
  branchSchema,
  commitSchema,
  pullSchema,
  issueSchema,
  runSchema,
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
  Runs,
} from "./shared";
const tabs = [
  "Overview",
  "Branches",
  "Commits",
  "Pull Requests",
  "Issues",
  "CI/CD",
];
function Branches({ path }: { path: string }) {
  const [page, setPage] = useState(1);
  const q = useGitHub(path + `&page=${page}`, pageSchema(branchSchema));
  return q.isPending ? (
    <Loading />
  ) : q.isError ? (
    <ErrorState error={q.error} />
  ) : (
    <>
      <div className="github-list">
        {q.data?.items.map((b) => (
          <article className="card github-row" key={b.name}>
            <strong>{b.name}</strong>
            <code>{b.sha.slice(0, 7)}</code>
            <span>{b.protected ? "Protected" : "Not protected"}</span>
          </article>
        ))}
        {!q.data?.items.length && <p>No branches on this page.</p>}
      </div>
      <Pagination page={page} next={!!q.data?.has_next} onPage={setPage} />
    </>
  );
}
function Commits({ path }: { path: string }) {
  const [page, setPage] = useState(1);
  const q = useGitHub(path + `&page=${page}`, pageSchema(commitSchema));
  return q.isPending ? (
    <Loading />
  ) : q.isError ? (
    <ErrorState error={q.error} />
  ) : (
    <>
      <div className="github-list">
        {q.data?.items.map((c) => (
          <article className="card github-row" key={c.sha}>
            <div>
              <External url={c.html_url}>
                <strong>{c.message}</strong>
              </External>
              <p>
                {c.author || "Author unavailable"} · {date(c.timestamp)}
              </p>
            </div>
            <code>{c.short_sha}</code>
          </article>
        ))}
        {!q.data?.items.length && <p>No commits on this page.</p>}
      </div>
      <Pagination page={page} next={!!q.data?.has_next} onPage={setPage} />
    </>
  );
}
function Pulls({ path }: { path: string }) {
  const [page, setPage] = useState(1);
  const [state, setState] = useState("open");
  const q = useGitHub(
    path + `&page=${page}&state=${state}`,
    pageSchema(pullSchema),
  );
  return (
    <>
      <label>
        Pull request state
        <select
          value={state}
          onChange={(e) => {
            setState(e.target.value);
            setPage(1);
          }}
        >
          <option>open</option>
          <option>closed</option>
          <option>all</option>
        </select>
      </label>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : (
        <>
          <div className="github-list">
            {q.data?.items.map((p) => (
              <article className="card github-row" key={p.number}>
                <div>
                  <External url={p.html_url}>
                    <strong>
                      #{p.number} {p.title}
                    </strong>
                  </External>
                  <p>
                    {p.author || "Author unavailable"} · {p.head} → {p.base} ·{" "}
                    {date(p.updated_at)}
                  </p>
                </div>
                <span className="badge">
                  {p.state}
                  {p.draft ? " · draft" : ""}
                </span>
              </article>
            ))}
            {!q.data?.items.length && <p>No pull requests on this page.</p>}
          </div>
          <Pagination page={page} next={!!q.data?.has_next} onPage={setPage} />
        </>
      )}
    </>
  );
}
function Issues({ path }: { path: string }) {
  const [page, setPage] = useState(1);
  const [state, setState] = useState("open");
  const q = useGitHub(
    path + `&page=${page}&state=${state}`,
    pageSchema(issueSchema),
  );
  return (
    <>
      <label>
        Issue state
        <select
          value={state}
          onChange={(e) => {
            setState(e.target.value);
            setPage(1);
          }}
        >
          <option>open</option>
          <option>closed</option>
          <option>all</option>
        </select>
      </label>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : (
        <>
          <div className="github-list">
            {q.data?.items.map((i) => (
              <article className="card github-row" key={i.number}>
                <div>
                  <External url={i.html_url}>
                    <strong>
                      #{i.number} {i.title}
                    </strong>
                  </External>
                  <p>
                    {i.author || "Author unavailable"} · {date(i.updated_at)} ·{" "}
                    {i.labels.join(", ")}
                  </p>
                </div>
                <span className="badge">{i.state}</span>
              </article>
            ))}
            {!q.data?.items.length && (
              <p>No issues on this page. Pull requests are excluded.</p>
            )}
          </div>
          <Pagination page={page} next={!!q.data?.has_next} onPage={setPage} />
        </>
      )}
    </>
  );
}
function RepoRuns({
  path,
  owner,
  repo,
  installation,
}: {
  path: string;
  owner: string;
  repo: string;
  installation: string;
}) {
  const [page, setPage] = useState(1);
  const q = useGitHub(path + `&page=${page}`, pageSchema(runSchema));
  return q.isPending ? (
    <Loading />
  ) : q.isError ? (
    <ErrorState error={q.error} />
  ) : (
    <>
      <Runs
        items={q.data?.items || []}
        owner={owner}
        repo={repo}
        installation={installation}
      />
      <Pagination page={page} next={!!q.data?.has_next} onPage={setPage} />
      <Link
        href={`/dashboard/cicd?installation=${installation}&owner=${owner}&repo=${repo}`}
      >
        Open CI/CD filters
      </Link>
    </>
  );
}
export function RepositoryDetail() {
  const params = useParams<{ owner: string; repo: string }>();
  const search = useSearchParams();
  const router = useRouter();
  const { owner, repo } = params;
  const installation = search.get("installation") || "";
  const tab = search.get("tab") || "Overview";
  const valid = validRepo(owner, repo) && validId(installation);
  const root = repoPath(owner, repo);
  const q = useGitHub(
    root + `?installation_id=${installation}`,
    repositorySchema,
    valid,
  );
  if (!valid)
    return (
      <>
        <Heading
          title="Invalid repository context"
          description="Open an authorized repository from the explorer."
        />
        <Link href="/dashboard/repositories">Back to repositories</Link>
      </>
    );
  return (
    <>
      <Heading
        title={`${owner}/${repo}`}
        description="Read development activity within the selected installation."
      />
      <Link href={`/dashboard/repositories?installation=${installation}`}>
        ← Repository explorer
      </Link>
      {q.isPending ? (
        <Loading />
      ) : q.isError ? (
        <ErrorState error={q.error} />
      ) : (
        q.data && (
          <>
            <nav className="github-tabs" aria-label="Repository sections">
              {tabs.map((t) => (
                <button
                  className="button secondary"
                  key={t}
                  aria-current={t === tab ? "page" : undefined}
                  onClick={() =>
                    router.replace(
                      `?installation=${installation}&tab=${encodeURIComponent(t)}`,
                    )
                  }
                >
                  {t}
                </button>
              ))}
            </nav>
            <section aria-label={`${tab} content`}>
              {tab === "Overview" && (
                <div className="card github-connection">
                  <h2>{q.data.full_name}</h2>
                  <p>{q.data.description || "No description provided."}</p>
                  <p>
                    {q.data.private ? "Private" : "Public"} ·{" "}
                    {q.data.language || "Language unavailable"} · {q.data.stars}{" "}
                    stars · {q.data.forks} forks
                  </p>
                  <p>
                    Default branch: {q.data.default_branch || "Unavailable"}
                  </p>
                  <p>
                    Updated: {date(q.data.updated_at)} · Last pushed:{" "}
                    {date(q.data.pushed_at)}
                  </p>
                  <External url={q.data.html_url}>Open on GitHub</External>
                </div>
              )}
              {tab === "Branches" && (
                <Branches
                  path={root + `/branches?installation_id=${installation}`}
                />
              )}{" "}
              {tab === "Commits" && (
                <Commits
                  path={root + `/commits?installation_id=${installation}`}
                />
              )}{" "}
              {tab === "Pull Requests" && (
                <Pulls path={root + `/pulls?installation_id=${installation}`} />
              )}{" "}
              {tab === "Issues" && (
                <Issues
                  path={root + `/issues?installation_id=${installation}`}
                />
              )}{" "}
              {tab === "CI/CD" && (
                <RepoRuns
                  path={root + `/actions/runs?installation_id=${installation}`}
                  owner={owner}
                  repo={repo}
                  installation={installation}
                />
              )}
            </section>
          </>
        )
      )}
    </>
  );
}
