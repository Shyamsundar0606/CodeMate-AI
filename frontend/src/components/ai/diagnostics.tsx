"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { useAuth } from "@/providers/auth-provider";
import { apiErrorMessage } from "@/lib/api/client";
import { aiStatusSchema, historySchema, investigationSchema, useAI, type RunContext } from "@/lib/ai";
import { Heading, Loading, ErrorState, Pagination } from "@/components/github/shared";

export function AnalyzeRun({ context, status, conclusion }: { context: RunContext; status: string; conclusion: string | null }) {
  const { session } = useAuth();
  const router = useRouter();
  const provider = useAI("/api/v1/ai/status", aiStatusSchema);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<unknown>(null);
  async function start() {
    if (pending) return;
    setPending(true); setError(null);
    try {
      const item = await session.post("/api/v1/auth/ai/investigations", investigationSchema, context);
      router.push("/dashboard/ai/investigations/" + item.id);
    } catch (failure) { setError(failure); }
    finally { setPending(false); }
  }
  if (status !== "completed") return <p>AI diagnosis is available after the workflow run completes.</p>;
  if (conclusion === "success") return <section className="card"><h3>No failure detected</h3><p>GitHub reports this run succeeded. No failure diagnosis or model call is needed.</p><Link href="/dashboard/ai">Investigation history</Link></section>;
  return <section className="card">
    <h3>Local AI failure diagnosis</h3>
    <p>Review evidence-based hypotheses and proposed verification steps. No changes will be applied.</p>
    {provider.isPending ? <Loading /> : provider.isError ? <ErrorState error={provider.error} retry={() => void provider.refetch()} /> :
      <p>{provider.data?.message}</p>}
    <button type="button" className="button primary" disabled={pending || !provider.data?.model_available}
      onClick={() => void start()}>{pending ? "Starting investigation..." : "Analyze with AI"}</button>
    {error !== null && <p role="alert">{apiErrorMessage(error)}</p>}
    <Link href="/dashboard/ai">View previous investigations</Link>
  </section>;
}

export function AIOverview() {
  const { session } = useAuth(); const router = useRouter();
  const [page, setPage] = useState(1);
  const submitting = useRef(false);
  const [startedId, setStartedId] = useState<string | null>(null);
  const [validationError, setValidationError] = useState("");
  const [modelChecked, setModelChecked] = useState(false);
  const [pending, setPending] = useState(false); const [error, setError] = useState<unknown>(null);
  const provider = useAI("/api/v1/ai/status", aiStatusSchema);
  const history = useAI("/api/v1/ai/investigations?page=" + page, historySchema);
  async function start(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (submitting.current) return;
    submitting.current = true;
    const fields = new FormData(event.currentTarget);
    setPending(true); setError(null); setValidationError("");
    try {
      const item = await session.post("/api/v1/auth/ai/investigations", investigationSchema, {
        owner: String(fields.get("owner")).trim(), repo: String(fields.get("repo")).trim(), installation_id: Number(fields.get("installation")),
        workflow_run_id: Number(fields.get("run")),
      });
      setStartedId(item.id);
      void history.refetch();
      router.push("/dashboard/ai/investigations/" + item.id);
    } catch (failure) { submitting.current = false; setError(failure); } finally { setPending(false); }
  }
  return <div className="ai-page">
    <Heading title="AI investigations" description="Local diagnosis, verified evidence and saved investigation history." />
    <section className="card">
      <h2>Local model</h2>
      {provider.isFetching || provider.isPending ? (
        <p role="status" aria-live="polite">Checking local model...</p>
      ) : provider.isError ? (
        <ErrorState error={provider.error} retry={() => { setModelChecked(true); void provider.refetch(); }} />
      ) : (
        <>
          <p>Selected model: {provider.data?.selected_model}</p>
          <p role="status" aria-live="polite">
            {modelChecked && "Check complete: "}
            {provider.data?.available && provider.data.model_available
              ? "Local model ready."
              : provider.data?.available
                ? "Ollama is running, but the selected model is not installed."
                : "Ollama is unavailable."}
          </p>
          <p>{provider.data?.message}</p>
        </>
      )}
      <p>This checks Ollama and the selected model through the authenticated backend. It does not check or start the investigation worker. Start the worker separately to process investigations.</p>
      <button type="button" className="button secondary" disabled={provider.isFetching || provider.isPending}
        onClick={() => { setModelChecked(true); void provider.refetch(); }}>
        {provider.isFetching ? "Checking local model..." : "Check local model"}
      </button>
    </section>
    <section className="card">
      <h2>Start investigation</h2>
      <p>Prefer <Link href="/dashboard/cicd">an authorized run in CI/CD monitoring</Link>, or enter its exact identifiers below. Access is checked by the backend.</p>
      <form onSubmit={event => void start(event)}
        onInvalid={event => { const field = event.target as HTMLInputElement; setValidationError("Check " + (field.labels?.[0]?.textContent || "the required fields") + ": " + field.validationMessage); }}>
        <div className="github-toolbar">
          <label>Repository owner<input name="owner" required maxLength={39} /></label>
          <label>Repository name<input name="repo" required maxLength={100} /></label>
          <label>Installation ID<input name="installation" type="number" min="1" max={Number.MAX_SAFE_INTEGER} step="1" required /></label>
          <label>Workflow run ID<input name="run" type="number" min="1" max={Number.MAX_SAFE_INTEGER} step="1" required /></label>
        </div>
        <button type="submit" className="button primary" disabled={pending || startedId !== null}>{pending ? "Starting investigation..." : "Start investigation"}</button>
        <p role="status" aria-live="polite" aria-atomic="true">{pending ? "Starting investigation..." : startedId ? "Investigation ready. Opening report..." : ""}</p>
        {startedId && <Link href={"/dashboard/ai/investigations/" + startedId}>Open investigation report</Link>}
        {validationError && <p role="alert">{validationError}</p>}
        <p>Successful runs receive a verified summary without invoking the model. Provider failures are saved with retry controls.</p>
        {error !== null && <div role="alert"><p>{apiErrorMessage(error)}</p><p>Check the identifiers and <Link href="/dashboard/github">review your GitHub connection</Link>, then submit again. If the request timed out, check recent investigations before trying again.</p></div>}
      </form>
    </section>
    <section className="card">
      <h2>Recent investigations</h2>
      {history.isPending ? <Loading /> : history.isError ? <ErrorState error={history.error} retry={() => void history.refetch()} /> :
        <><p>Completed: {history.data?.completed_count} | Failed analyses: {history.data?.failed_count}</p>
          {!history.data?.items.length && <p>No investigations yet.</p>}
          <div className="github-list">{history.data?.items.map(item => <article key={item.id} className="card">
            <Link href={"/dashboard/ai/investigations/" + item.id}>{item.owner}/{item.repo} | Run {item.workflow_run_id}</Link>
            <p>{item.status} | {new Date(item.created_at).toLocaleString()}</p>
          </article>)}</div>
          <Pagination page={page} next={!!history.data?.has_next} onPage={setPage} />
        </>}
      <button type="button" className="button secondary" onClick={() => void history.refetch()}>Refresh history</button>
    </section>
  </div>;
}

export function InvestigationReport() {
  const { id } = useParams<{ id: string }>();
  if (!/^[0-9a-f-]{36}$/i.test(id)) return <p role="alert">Invalid investigation identifier.</p>;
  return <Report key={id} id={id} />;
}
function Report({ id }: { id: string }) {
  const { session } = useAuth(); const router = useRouter();
  const query = useAI("/api/v1/ai/investigations/" + id, investigationSchema, true);
  const [pending, setPending] = useState(false); const [error, setError] = useState<unknown>(null);
  const [notice, setNotice] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshNotice, setRefreshNotice] = useState("");
  const [refreshError, setRefreshError] = useState<unknown>(null);
  async function refresh() {
    if (refreshing || query.isFetching) return;
    setRefreshing(true); setRefreshNotice(""); setRefreshError(null);
    try {
      const result = await query.refetch();
      if (result.isError) throw result.error;
      setRefreshNotice("Investigation updated");
    } catch (failure) { setRefreshError(failure); }
    finally { setRefreshing(false); }
  }
  async function action(kind: "retry" | "cancel" | "delete") {
    if (pending) return;
    if ((kind === "delete" || kind === "cancel") && !window.confirm(kind === "delete" ? "Delete this saved report and evidence?" : "Cancel this investigation? In-flight local inference may finish before cancellation is observed.")) return;
    setPending(true); setError(null);
    try {
      if (kind === "delete") {
        await session.post(`/api/v1/auth/ai/investigations/${id}/delete`, undefined);
        router.push("/dashboard/ai"); return;
      }
      await session.post(`/api/v1/auth/ai/investigations/${id}/${kind}`, investigationSchema);
      await query.refetch();
    } catch (failure) { setError(failure); } finally { setPending(false); }
  }
  async function copy() {
    if (!window.confirm("Redaction is imperfect. Review evidence for secrets before sharing. Copy this report?")) return;
    try { await navigator.clipboard.writeText(JSON.stringify(query.data?.report, null, 2)); setNotice("Copied report. Review before sharing."); }
    catch { setNotice("Clipboard unavailable. Select the report text manually."); }
  }
  if (query.isPending) return <Loading />;
  if (query.isError && !query.data) return <ErrorState error={query.error} retry={() => void refresh()} />;
  const item = query.data; if (!item) return null;
  const report = item.report; const active = ["queued", "running"].includes(item.status);
  return <div className="ai-page">
    <Heading title="Investigation report" description={item.owner + "/" + item.repo + " | Run " + item.workflow_run_id} />
    <Link href="/dashboard/ai">Investigation history</Link>
    <section className="card">
      <p role="status" aria-live="polite">Analysis: {item.status} | Stage: {item.stage}</p>
      <p>Attempt {item.attempts} of {item.max_attempts}</p>
      <p>Created: {new Date(item.created_at).toLocaleString()} | Completed: {item.completed_at ? new Date(item.completed_at).toLocaleString() : "Pending"}</p>
      {active && <p>Queued work survives API restarts. Start the worker if progress stops. Polling stops after ten minutes; refresh manually to check later.</p>}
      {item.error_message && <p role="alert">{item.error_message}</p>}
      <div className="github-toolbar">
        <button type="button" className="button secondary" disabled={refreshing || query.isFetching}
          onClick={() => void refresh()}>{refreshing ? "Refreshing investigation..." : "Refresh investigation"}</button>
        {active && <button className="button secondary" disabled={pending} onClick={() => void action("cancel")}>Cancel investigation</button>}
        {item.status === "failed" && item.attempts < item.max_attempts && <button className="button primary" disabled={pending} onClick={() => void action("retry")}>Retry investigation</button>}
        {!active && <button className="button secondary" disabled={pending} onClick={() => void action("delete")}>Delete investigation</button>}
      </div>
      <p role="status" aria-live="polite" aria-atomic="true">
        {refreshing ? "Refreshing investigation..." : refreshNotice}
      </p>
      {(refreshError !== null || query.isError) && <>
        <p>Refresh failed. Showing the previously loaded report.</p>
        <ErrorState error={refreshError ?? query.error} retry={() => void refresh()} />
      </>}
      {error !== null && <p role="alert">{apiErrorMessage(error)}</p>}
    </section>
    {report && <>
      <section className="card">
        <h2>{report.failure_category === "no_failure" ? "No failure detected" : "Diagnostic summary"}</h2>
        <p>{report.summary}</p><p>Category: {report.failure_category.replaceAll("_", " ")}</p>
        <p>Workflow: {report.workflow_name || "Unavailable"} | Branch: {report.branch || "Unavailable"} | Run: {report.run_conclusion}</p>
        <p>Commit: <code>{report.commit_sha}</code></p>
        <p>Model: {report.model_name || "Deterministic metadata summary"} | Evidence: {report.evidence_completeness}</p>
        <p>Analyzed jobs: {report.analyzed_job_ids.join(", ") || "None available"}</p>
      </section>
      {report.findings.map(finding => <section className="card" key={finding.id}>
        <h2>{finding.title}</h2><p>Severity: {finding.severity} | Confidence: {finding.confidence}</p>
        <p>{finding.description}</p>
        <h3>Observed evidence</h3>
        {finding.evidence.map((claim, index) => <div key={index}>
          <Link href={"#evidence-" + claim.evidence_id}>Open evidence {claim.evidence_id}</Link><blockquote>{claim.quote}</blockquote>
        </div>)}
        <h3>Root-cause hypothesis</h3><p>{finding.root_cause_hypothesis}</p>
        <h3>Suggested change (not applied)</h3><p>{finding.suggested_fix}</p>
        <h3>Recommended verification</h3><ul>{finding.verification_steps.map((step,index) => <li key={index}>{step}</li>)}</ul>
      </section>)}
      <section className="card">
        <h2>Supporting evidence</h2>
        {!report.evidence.length && <p>No log evidence was collected. See the report limitations.</p>}
        {report.evidence.map(evidence => <details className="ai-evidence" id={"evidence-" + evidence.id} key={evidence.id}>
          <summary>{evidence.id} | {evidence.source} | Job {evidence.job_id || "N/A"}</summary>
          <p>Step metadata: {evidence.step || "Unavailable"} | Lines {evidence.line_start || "N/A"} - {evidence.line_end || "N/A"}</p>
          <p>Redacted: {evidence.redacted ? "yes" : "no"} | Truncated: {evidence.truncated ? "yes" : "no"}</p>
          <pre>{evidence.excerpt}</pre>
        </details>)}
      </section>
      <section className="card"><h2>Recommended actions</h2><ul>{report.recommended_actions.map((text,index) => <li key={index}>{text}</li>)}</ul>
        <h2>Limitations and privacy</h2><ul>{report.limitations.map((text,index) => <li key={index}>{text}</li>)}</ul>
        <p>Generated hypotheses may be wrong. Redaction cannot detect every secret. Review excerpts before sharing. No commands or changes have been executed.</p>
        <button className="button secondary" onClick={() => void copy()}>Copy report</button>
        {notice && <p role="status">{notice}</p>}
      </section>
    </>}
  </div>;
}
