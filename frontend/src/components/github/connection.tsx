"use client";
import Link from "next/link";
import Image from "next/image";
import { useEffect, useRef, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { GitHubMark } from "./mark";
import { useAuth } from "@/providers/auth-provider";
import { apiErrorMessage } from "@/lib/api/client";
import {
  useGitHub,
  connectionSchema,
  connectSchema,
  disconnectSchema,
  authorizationUrl,
  date,
} from "@/lib/github";
import { Heading, ErrorState, Loading, External } from "./shared";
const callbackMessages: Record<string, string> = {
  connected: "GitHub authorization returned. Checking your saved connection...",
  github_authorization_cancelled: "GitHub authorization was cancelled.",
  github_invalid_state:
    "Authorization state was invalid or expired. Start again from this browser.",
  github_missing_code: "GitHub did not return an authorization code.",
  github_session_changed:
    "Your CodeMate session changed. Sign in and reconnect.",
  github_account_already_linked:
    "That GitHub account is linked to another CodeMate account.",
  github_authorization_failed: "GitHub authorization failed. Start again.",
  github_not_configured: "GitHub integration is not configured.",
};
export function GitHubConnectionPage() {
  const query = useGitHub("/api/v1/github/connection", connectionSchema);
  const { session } = useAuth();
  const queries = useQueryClient();
  const params = useSearchParams();
  const router = useRouter();
  const dialog = useRef<HTMLDialogElement>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(() => {
    const initial = params.get("github_result");
    return initial
      ? callbackMessages[initial] ||
          "GitHub authorization could not be completed. Review your connection and try again."
      : "";
  });
  const result = params.get("github_result");
  useEffect(() => {
    if (result) {
      void queries.invalidateQueries({ queryKey: ["github"] });
      router.replace("/dashboard/github");
    }
  }, [result, queries, router]);
  async function connect() {
    setBusy(true);
    setNotice("");
    try {
      const value = await session.post(
        "/api/v1/auth/github/connect",
        connectSchema,
      );
      window.location.assign(authorizationUrl(value.authorization_url));
    } catch (error) {
      setNotice(apiErrorMessage(error));
      setBusy(false);
    }
  }
  async function disconnect() {
    setBusy(true);
    try {
      const value = await session.post(
        "/api/v1/auth/github/disconnect",
        disconnectSchema,
      );
      if (!value.disconnected)
        throw new Error("Disconnection was not confirmed.");
      queries.removeQueries({ queryKey: ["github"] });
      setNotice(value.message);
      dialog.current?.close();
      void query.refetch();
    } catch (error) {
      setNotice(apiErrorMessage(error));
    } finally {
      setBusy(false);
    }
  }
  const data = query.data;
  return (
    <>
      <Heading
        title="GitHub connection"
        description="Authorize a GitHub App with read-only repository permissions."
      />
      {notice && (
        <div className="github-notice card" role="status">
          {notice}
        </div>
      )}
      {query.isPending ? (
        <Loading />
      ) : query.isError ? (
        <ErrorState error={query.error} retry={() => void query.refetch()} />
      ) : (
        data && (
          <section className="card github-connection">
            <GitHubMark size={36} />
            <h2>
              {data.status === "connected"
                ? `Connected as ${data.github_login}`
                : data.status === "reauthorization_required"
                  ? "Reconnect GitHub"
                  : "Connect your GitHub account"}
            </h2>
            {data.github_avatar_url &&
              /^https:\/\/avatars\.githubusercontent\.com\/u\/[0-9]+\?v=4$/.test(
                data.github_avatar_url,
              ) && (
                <Image
                  src={data.github_avatar_url}
                  alt={`${data.github_login} avatar`}
                  width={64}
                  height={64}
                  unoptimized
                />
              )}
            <p>{data.github_display_name}</p>
            <span className="badge">{data.status.replaceAll("_", " ")}</span>
            <p>
              Read repository metadata, branches, commits, issues, pull
              requests, workflows, jobs and available logs. GitHub App
              installation and your own GitHub access determine the repositories
              available here.
            </p>
            <p>
              Credentials remain encrypted on the backend. CodeMate does not
              request repository or workflow write permissions.
            </p>
            {!data.configured && (
              <div className="github-notice" role="status">
                <strong>GitHub integration not configured</strong>
                <ol>
                  <li>
                    Create the GitHub App using{" "}
                    <code>docs/GITHUB_INTEGRATION.md</code>.
                  </li>
                  <li>
                    Select the five read-only repository permissions and
                    configure the backend callback.
                  </li>
                  <li>
                    Set the backend client ID, client secret and independent
                    encryption key, then restart FastAPI.
                  </li>
                </ol>
              </div>
            )}
            <div className="github-toolbar">
              {data.status !== "connected" && (
                <button
                  className="button primary"
                  disabled={busy || !data.configured}
                  onClick={() => void connect()}
                >
                  {busy ? "Connecting..." : "Connect GitHub"}
                </button>
              )}
              {data.status !== "disconnected" && (
                <button
                  className="button secondary"
                  disabled={busy}
                  onClick={() => dialog.current?.showModal()}
                >
                  Disconnect GitHub
                </button>
              )}
              {data.status === "connected" && (
                <Link className="button primary" href="/dashboard/repositories">
                  Explore repositories
                </Link>
              )}
              {data.install_url && (
                <External url={data.install_url}>
                  Install App / choose repositories
                </External>
              )}
            </div>
            <p>Last verified: {date(data.last_verified_at)}</p>
            {Object.keys(data.granted_permissions).length > 0 && (
              <p>
                Reported installation permissions:{" "}
                {Object.entries(data.granted_permissions)
                  .map(([key, value]) => `${key}: ${value}`)
                  .join(", ")}
                . These describe returned installations, not access to every
                repository.
              </p>
            )}
          </section>
        )
      )}
      <dialog
        ref={dialog}
        className="github-dialog"
        aria-labelledby="disconnect-title"
      >
        <h2 id="disconnect-title">Disconnect GitHub?</h2>
        <p>
          This deletes CodeMate&apos;s stored credentials and attempts to revoke
          this App&apos;s authorization for your GitHub account. Repository
          content is unaffected.
        </p>
        <div className="github-toolbar">
          <button
            className="button secondary"
            disabled={busy}
            onClick={() => dialog.current?.close()}
          >
            Keep connection
          </button>
          <button
            className="button primary"
            disabled={busy}
            onClick={() => void disconnect()}
          >
            Confirm disconnect
          </button>
        </div>
      </dialog>
    </>
  );
}
