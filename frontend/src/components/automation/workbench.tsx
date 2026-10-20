"use client";
import Link from "next/link";
import { SandboxPanel } from "@/components/automation/sandbox-panel";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/providers/auth-provider";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import { useAI } from "@/lib/ai";
import { useGitHub, pageSchema, repositorySchema } from "@/lib/github";
import { InstallationPicker } from "@/components/github/repositories";
import { automationSchema, automationHistorySchema, type Automation } from "@/lib/automation";

export function AutomationWorkbench() {
  const { user } = useAuth();
  return <Workbench key={user?.id || "anonymous"} />;
}
function Workbench() {
  const { session } = useAuth();
  const [installation, setInstallation] = useState("");
  const [repository, setRepository] = useState("");
  const [paths, setPaths] = useState("");
  const [run, setRun] = useState("");
  const [request, setRequest] = useState("");
  const [mode, setMode] = useState<"explain" | "patch">("patch");
  const [workspace, setWorkspace] = useState<Automation | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("Select an authorized repository and source files to inspect.");
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState<string | null>(null);
  const [targets, setTargets] = useState<string[]>([]);
  const active = useRef(false);
  const generation = useRef(0);
  const requestId = useRef<string | null>(null);
  const proposalRequest = useRef<{ key: string; id: string } | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const feedback = useRef<HTMLDivElement>(null);
  const explanation = useRef<HTMLElement>(null);
  const focusTarget = useRef<"result" | "feedback" | null>(null);
  const history = useAI("/api/v1/automation/sessions", automationHistorySchema);
  const repositories = useGitHub(`/api/v1/github/repositories?installation_id=${installation || "0"}&per_page=100`, pageSchema(repositorySchema), !!installation);
  useEffect(() => () => { generation.current++; }, []);
  useEffect(() => { if (confirm) dialog.current?.showModal(); else dialog.current?.close(); }, [confirm]);
  useEffect(() => {
    const target = focusTarget.current;
    if (!target) return;
    focusTarget.current = null;
    const element = target === "result" ? explanation.current : feedback.current;
    element?.focus(); element?.scrollIntoView?.({ block: "nearest" });
  }, [workspace, error, notice]);
  async function task(label: string, action: () => Promise<Automation>, suggestion = false) {
    if (active.current) return;
    active.current = true; const current = generation.current; setBusy(true); setError(""); setNotice(label);
    try {
      const result = await action();
      if (current !== generation.current) return;
      const saved = result.proposals.findLast(p => p.request === request && p.mode === mode);
      if (suggestion && !saved) throw new ApiError("No saved suggestion was returned. Reload this session before retrying.", undefined, "protocol");
      focusTarget.current = suggestion ? "result" : "feedback";
      setWorkspace(result); setNotice(suggestion ? (saved?.mode === "explain" ? "Source explanation saved. No files changed and no validation ran." : "Patch proposal saved for review. No files changed and no validation ran.") : "Automation updated. No patch has been applied and no validation has run.");
      void history.refetch();
    } catch (failure) { if (current === generation.current) { focusTarget.current = "feedback"; setError(apiErrorMessage(failure)); setNotice("Request failed. The saved state is not confirmed. Reload the session before retrying; unchanged retries reuse the same request identifier."); } }
    finally { active.current = false; setBusy(false); }
  }
  const selected = workspace?.proposals.find(p => p.id === confirm);
  async function decision(id: string, value: "approve" | "reject" | "cancel") {
    if (!workspace) return;
    const proposal = workspace.proposals.find(p => p.id === id);
    if (!proposal) return;
    await task("Recording proposal decision...", () => session.post(`/api/v1/auth/automation/sessions/${workspace.id}/proposals/${id}/decision`, automationSchema, { workspace_id: workspace.workspace_id, base_sha: workspace.base_sha, patch_hash: proposal.patch_hash, decision: value, validations: value === "approve" ? targets : [] }));
    setConfirm(null); setTargets([]);
  }
  return <section className="automation-workbench">
    <div className="page-heading"><span className="eyebrow">LOCAL AI / REVIEW FIRST</span><h1>Developer Automation</h1><p>Inspect pinned source and review AI suggestions. GitHub access is read-only.</p><Link href="/dashboard/voice">Use Voice Agent</Link></div>
    <div className="card"><h2>Execution unavailable</h2><p>Patch application and validation are disabled until an isolated runner is verified. Approval records review only. No application files or repository checkout are modified.</p></div>
    <div ref={feedback} tabIndex={-1}><p role="status" aria-live="polite">{notice}</p>{error && <div role="alert"><p>{error}</p><p>Check GitHub authorization and local Ollama readiness. After a timeout, reload this session before retrying to check for a saved suggestion.</p></div>}</div>
    <form className="card automation-form" onSubmit={event => { event.preventDefault(); if (!repository || !installation || !paths.trim()) return; const [owner, repo] = repository.split("/"); requestId.current ||= crypto.randomUUID(); void task("Inspecting authorized source...", () => session.post("/api/v1/auth/automation/sessions", automationSchema, { request_id: requestId.current, owner, repo, installation_id: Number(installation), workflow_run_id: run ? Number(run) : null, paths: paths.split(/[,\n]/).map(p => p.trim()).filter(Boolean) })); }}>
      <h2>Authorized source snapshot</h2><fieldset disabled={busy}><InstallationPicker value={installation} onChange={value => { setInstallation(value); setRepository(""); requestId.current = null; }} />
      <label>Repository<select required value={repository} onChange={event => { setRepository(event.target.value); requestId.current = null; }}><option value="">Choose a repository</option>{repositories.data?.items.map(repo => <option key={repo.id} value={repo.full_name}>{repo.full_name}</option>)}</select></label>
      {repositories.isError && <p role="alert">{apiErrorMessage(repositories.error)}</p>}
      <p className="small muted">Repository selector shows the first 100 repositories of the selected installation.</p>
      <label>Source paths<textarea required maxLength={724} value={paths} onChange={event => { setPaths(event.target.value); requestId.current = null; }} placeholder="backend/app/main.py, frontend/src/lib/voice.ts" /></label>
      <p>Up to four existing UTF-8 source files, 12 KB each and 24 KB total. Secret files, symlinks and executable files are rejected.</p>
      <label>Workflow run ID (optional)<input inputMode="numeric" pattern="[1-9][0-9]{0,15}" value={run} onChange={event => { setRun(event.target.value); requestId.current = null; }} /></label>
      <button type="submit" className="button primary" disabled={busy || !repository || !paths.trim()}>Inspect source</button></fieldset>
    </form>
    {workspace && <><div className="card"><h2>Snapshot context</h2><button type="button" disabled={busy} onClick={() => void task("Reloading automation session...", () => session.get(`/api/v1/automation/sessions/${workspace.id}`, automationSchema))}>Reload session</button><p>{workspace.repository}</p><p>Commit: <code>{workspace.base_sha}</code></p><p>Workspace: <code>{workspace.workspace_id}</code></p><p>Expires: {new Date(workspace.expires_at).toLocaleString()}</p><ul>{workspace.files.map(path => <li key={path}>{path}</li>)}</ul><h3>Retrieved CI evidence</h3>{Object.entries(workspace.evidence).map(([key, text]) => <details key={key}><summary>{key}</summary><pre>{text}</pre></details>)}{!Object.keys(workspace.evidence).length && <p>No CI run selected. Suggestions use the inspected source only.</p>}</div>
    <form className="card automation-form" onSubmit={event => { event.preventDefault(); const key = JSON.stringify([workspace.id, request, mode]); if (proposalRequest.current?.key !== key) proposalRequest.current = { key, id: crypto.randomUUID() }; void task("Generating and validating local AI suggestion...", () => session.post(`/api/v1/auth/automation/sessions/${workspace.id}/proposals`, automationSchema, { request, mode, request_id: proposalRequest.current?.id }), true); }}><h2>Request a suggestion</h2><fieldset disabled={busy}><label>Developer request<textarea required minLength={3} maxLength={1000} value={request} onChange={event => setRequest(event.target.value)} /></label><label>Suggestion type<select value={mode} onChange={event => setMode(event.target.value as "patch" | "explain")}><option value="patch">Propose a patch</option><option value="explain">Explain source</option></select></label><button className="button primary" type="submit" disabled={busy}>Generate suggestion</button></fieldset></form>
    {workspace.proposals.map((proposal, index) => <article ref={index === workspace.proposals.length - 1 ? explanation : undefined} tabIndex={-1} className="card" key={proposal.id}><h2>{proposal.mode === "patch" ? "Patch proposal" : "Source explanation"}</h2><p>Status: <strong>{proposal.status.replaceAll("_", " ")}</strong></p><p>AI interpretation, unverified. Citation checks confirm source provenance only. Confidence: {proposal.suggestion.confidence}</p><p>{proposal.suggestion.explanation}</p><p>Expected improvement: {proposal.suggestion.expected_improvement}</p><h3>Changed files</h3><ul>{proposal.files.map(path => <li key={path}>{path}</li>)}</ul>{proposal.diff && <pre tabIndex={0} aria-label="Proposed unified diff">{proposal.diff}</pre>}<p>Patch hash: <code>{proposal.patch_hash}</code></p><h3>Evidence</h3>{proposal.suggestion.evidence.map((citation, i) => <blockquote key={i}><strong>{citation.source}</strong>{citation.evidence_id && <span> / {citation.evidence_id} / lines {citation.line_start}-{citation.line_end}</span>}<p>{citation.quote}</p></blockquote>)}<h3>Potential risks and limitations</h3><p>Risk statements are unverified hypotheses requiring independent review. Source citations do not establish a vulnerability.</p><ul>{[...proposal.suggestion.risks, ...proposal.suggestion.limitations].map((text, i) => <li key={i}>{text}</li>)}</ul><p>Suggested validation targets (not executed): {proposal.suggestion.validations.join(", ") || "None"}</p><p>Expires: {new Date(proposal.expires_at).toLocaleString()}</p>{proposal.status === "awaiting_approval" && <div className="button-row"><button disabled={busy} onClick={() => { setTargets([]); setConfirm(proposal.id); }}>Review approval</button><button disabled={busy} onClick={() => void decision(proposal.id, "reject")}>Reject proposal</button><button disabled={busy} onClick={() => void decision(proposal.id, "cancel")}>Cancel proposal</button></div>}<p>Application: not applied. Validation: not run.</p><button disabled>Apply patch and run validation (unavailable)</button></article>)}
    <div className="card"><h2>Audit history</h2><ul>{workspace.audit.map((event, i) => <li key={i}>{event.event.replaceAll("_", " ")} at {new Date(event.at).toLocaleString()}</li>)}</ul></div></>}
    <SandboxPanel pending={busy} key={workspace?.proposals.findLast(p => p.status === "approved")?.id || "history"} sessionId={workspace?.id} proposalId={workspace?.proposals.findLast(p => p.status === "approved")?.id} />
    <div className="card"><h2>Recent automation sessions</h2>{history.isError && <p role="alert">{apiErrorMessage(history.error)}</p>}{history.isPending && <p>Loading history...</p>}{history.data?.map(item => <button key={item.id} disabled={busy} onClick={() => void task("Loading automation...", () => session.get(`/api/v1/automation/sessions/${item.id}`, automationSchema))}>{item.repository} / {item.base_sha.slice(0, 8)}</button>)}</div>
    <dialog ref={dialog} aria-labelledby="approval-title" onCancel={event => { if (busy) event.preventDefault(); else setConfirm(null); }} onClose={() => setConfirm(null)}>{selected && <><h2 id="approval-title">Approve exact patch for review</h2><p>Repository: {workspace?.repository}</p><p>Base: <code>{workspace?.base_sha}</code></p><p>Patch hash: <code>{selected.patch_hash}</code></p><pre tabIndex={0} aria-label="Approval diff">{selected.diff}</pre><p>This records approval only. It does not apply a patch or run tests. A future runner must require fresh execution approval.</p><fieldset disabled={busy}><legend>Record suggested validation choices (not executed)</legend>{selected.suggestion.validations.map(target => <label key={target}><input type="checkbox" checked={targets.includes(target)} onChange={event => setTargets(event.target.checked ? [...targets, target] : targets.filter(t => t !== target))} />{target}</label>)}</fieldset><button disabled={busy} onClick={() => void decision(selected.id, "approve")}>Confirm review approval</button><button disabled={busy} onClick={() => setConfirm(null)}>Back to proposal</button></>}</dialog>
  </section>;
}
