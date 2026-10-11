"use client";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import {
  useGitHub,
  pageSchema,
  installationSchema,
  repositorySchema,
  date,
  validId,
  type Repository,
} from "@/lib/github";
import { Heading, Loading, ErrorState, Pagination, External } from "./shared";
export function InstallationPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const [page, setPage] = useState(1);
  const query = useGitHub(
    `/api/v1/github/installations?page=${page}`,
    pageSchema(installationSchema),
  );
  return (
    <div className="card github-picker">
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : (
        <>
          <label>
            App installation
            <select
              value={value}
              onChange={(event) => onChange(event.target.value)}
            >
              <option value="">Choose an authorized installation</option>
              {query.data?.items.map((item) => (
                <option key={item.id} value={item.id} disabled={item.suspended}>
                  {item.account} · {item.repository_selection} repositories
                  {item.suspended ? " · suspended" : ""}
                </option>
              ))}
            </select>
          </label>
          {!query.data?.items.length && (
            <p>
              No accessible App installations. Install the App on selected
              repositories from the GitHub connection page.
            </p>
          )}
          <Pagination
            page={page}
            next={!!query.data?.has_next}
            onPage={(p) => {
              setPage(p);
              onChange("");
            }}
          />
        </>
      )}
    </div>
  );
}
export function RepositoryCard({
  repo,
  installation,
}: {
  repo: Repository;
  installation: string;
}) {
  return (
    <article className="card repository-card">
      <div className="card-heading">
        <Link
          href={`/dashboard/repositories/${encodeURIComponent(repo.owner)}/${encodeURIComponent(repo.name)}?installation=${installation}`}
        >
          <h2>{repo.full_name}</h2>
        </Link>
        <span className="badge">
          {repo.private ? "Private" : "Public"}
          {repo.fork ? " · fork" : ""}
        </span>
      </div>
      <p>{repo.description || "No description provided."}</p>
      <p>
        {repo.language || "Language unavailable"} · {repo.stars} stars ·{" "}
        {repo.forks} forks
      </p>
      <p>Updated {date(repo.updated_at)}</p>
      <External url={repo.html_url}>Open on GitHub</External>
    </article>
  );
}
export function RepositoryExplorer() {
  const params = useSearchParams();
  const router = useRouter();
  const installation = params.get("installation") || "";
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("updated");
  const query = useGitHub(
    `/api/v1/github/repositories?installation_id=${installation}&page=${page}&q=${encodeURIComponent(search)}&sort=${sort}`,
    pageSchema(repositorySchema),
    validId(installation),
  );
  return (
    <>
      <Heading
        title="Repositories"
        description="Explore repositories available through a selected GitHub App installation."
      />
      <InstallationPicker
        value={installation}
        onChange={(value) => {
          setPage(1);
          router.replace(
            `/dashboard/repositories${value ? `?installation=${value}` : ""}`,
          );
        }}
      />
      {validId(installation) && (
        <>
          <div className="github-toolbar">
            <label>
              Search this page
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Repository name or description"
              />
            </label>
            <label>
              Sort this page
              <select
                value={sort}
                onChange={(event) => setSort(event.target.value)}
              >
                <option value="updated">Recently updated</option>
                <option value="name">Name</option>
                <option value="stars">Stars</option>
              </select>
            </label>
            <button
              className="button secondary"
              onClick={() => void query.refetch()}
            >
              Refresh repositories
            </button>
          </div>
          <p className="muted">
            Search and sorting apply to the current authorized page.
            Installation total: {query.data?.total ?? "unavailable"}; this is
            not an account-wide total.
          </p>
          {query.isPending ? (
            <Loading />
          ) : query.isError ? (
            <ErrorState error={query.error} />
          ) : (
            <>
              <div className="repository-grid">
                {query.data?.items.map((repo) => (
                  <RepositoryCard
                    repo={repo}
                    installation={installation}
                    key={repo.id}
                  />
                ))}
              </div>
              {query.data?.items.length === 0 && (
                <div className="card github-notice">
                  No repositories match on this page. Check another page or
                  GitHub’s selected repository settings.
                </div>
              )}
              <Pagination
                page={page}
                next={!!query.data?.has_next}
                onPage={setPage}
              />
            </>
          )}
        </>
      )}
    </>
  );
}
