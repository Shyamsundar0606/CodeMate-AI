"use client";

import { useRef, useState } from "react";
import { z } from "zod";
import { useAuth } from "@/providers/auth-provider";
import { useAI } from "@/lib/ai";
import { apiErrorMessage } from "@/lib/api/client";
import { executionHistorySchema, executionPreviewSchema, sandboxCapabilitySchema, type ExecutionPreview } from "@/lib/sandbox";

export function SandboxPanel({ sessionId, proposalId, pending = false }: { sessionId?: string; proposalId?: string; pending?: boolean }) {
  const { session } = useAuth();
  const capability = useAI("/api/v1/sandbox/capabilities", sandboxCapabilitySchema);
  const parsedCapability = sandboxCapabilitySchema.safeParse(capability.data);
  const history = useAI("/api/v1/sandbox/executions", executionHistorySchema);
  const [preview, setPreview] = useState<ExecutionPreview | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [profile, setProfile] = useState("python_syntax");
  const active = useRef(false);
  const requestId = useRef<string | null>(null);
  async function mutate(path: `/api/v1/auth/sandbox/${string}`, body: unknown, schema: z.ZodType<ExecutionPreview> = executionPreviewSchema) {
    if (active.current || pending) return;
    active.current = true; setBusy(true); setError("");
    try { setPreview(await session.post(path, schema, body)); void history.refetch(); }
    catch (failure) { setError(apiErrorMessage(failure)); }
    finally { active.current = false; setBusy(false); }
  }
  async function load(id: string) {
    if (active.current || pending) return;
    active.current = true; setBusy(true); setError("");
    try { setPreview(await session.get(`/api/v1/sandbox/executions/${id}`, executionPreviewSchema)); }
    catch (failure) { setError(apiErrorMessage(failure)); }
    finally { active.current = false; setBusy(false); }
  }
  return <section className="card" aria-label="Sandbox execution preparation">
    <h2>Sandbox readiness and execution preview</h2>
    <p>Execution disabled. Isolation verification is required before application or validation. Review approval requires a separate execution confirmation.</p>
    {capability.isPending && <p role="status">Checking sandbox readiness...</p>}
    {capability.isError && <p role="alert">Sandbox unavailable. {apiErrorMessage(capability.error)}</p>}
    {capability.data && !parsedCapability.success && <p role="alert">Runner readiness response is invalid. Execution remains disabled.</p>}
    {parsedCapability.success && <ul>{parsedCapability.data.reasons.map(reason => <li key={reason}>{reason}</li>)}</ul>}
    {parsedCapability.success && <div aria-label="Runner admission requirements">
      <h3>Runner admission: blocked</h3>
      <p>Preparation only. These requirements are not runtime progress or execution approval.</p>
      <ul>{parsedCapability.data.readiness.checks.map(check => <li key={check.id}>
        <strong>{check.label}</strong>: {check.status.replaceAll("_", " ")}<p>{check.reason}</p>
      </li>)}</ul>
    </div>}
    {proposalId && <><label>Validation profile<select value={profile} disabled={busy || pending} onChange={event => { setProfile(event.target.value); requestId.current = null; }}><option value="python_syntax">Python syntax (preparation only)</option></select></label>
      <p>Only approved Python changes are supported. Preparing a preview does not create a filesystem workspace.</p>
      <button disabled={busy || pending} onClick={() => { requestId.current ||= crypto.randomUUID(); void mutate("/api/v1/auth/sandbox/executions", { request_id: requestId.current, session_id: sessionId, proposal_id: proposalId, profiles: [profile] }); }}>Prepare execution preview</button></>}
    {error && <p role="alert">{error}</p>}
    {preview && <div>
      <h3>Exact execution preview</h3><p>State: {preview.state.replaceAll("_", " ")}</p>
      <p>Repository: {preview.preview.repository}</p><p>Commit: <code>{preview.preview.base_sha}</code></p>
      <p>Proposal: <code>{preview.preview.proposal_id}</code></p><p>Patch hash: <code>{preview.preview.patch_hash}</code></p>
      <p>Confirmation binding: <code>{preview.binding_hash}</code></p><p>Expires: {new Date(preview.expires_at).toLocaleString()}</p>
      <ul>{preview.preview.files.map(file => <li key={file}>{file}</li>)}</ul><pre tabIndex={0} aria-label="Execution preview diff">{preview.preview.diff}</pre>
      <h3>Expected file hashes (not applied)</h3><ul>{preview.preview.expected_manifest.map(item => <li key={item.path}>{item.path}<p>Before: <code>{item.before_sha256}</code></p><p>Expected after: <code>{item.after_sha256}</code></p></li>)}</ul>
      <h3>Proposed validation command</h3>{preview.preview.profiles.map(item => <div key={item.id}><pre tabIndex={0} aria-label="Proposed validation command">{item.argv.join(" ")}</pre><p>{item.description}</p></div>)}
      <p>Isolation profile: {preview.preview.isolation.version}. Image digest: unverified. Network: none.</p>
      <p>Proposed limits: {preview.preview.isolation.memory_mib} MiB memory, {preview.preview.isolation.pids} processes, {preview.preview.isolation.timeout_seconds} seconds, {preview.preview.isolation.output_bytes} output bytes. These controls have not been verified.</p>
      <p>Patch not applied. Validation not executed. No exit code or test output exists.</p>
      <button disabled>Run in isolated sandbox (execution disabled)</button>
      <button disabled={busy || pending || preview.state !== "awaiting_confirmation"} onClick={() => void mutate(`/api/v1/auth/sandbox/executions/${preview.id}/cancel`, {})}>Cancel execution preview</button>
      <h3>Execution audit events</h3><ul>{preview.audit.map((event, i) => <li key={i}>{event.event.replaceAll("_", " ")} at {new Date(event.at).toLocaleString()}</li>)}</ul>
    </div>}
    <h3>Execution history</h3><p>Preparation records only. No jobs have been executed.</p>
    {history.isError && <p role="alert">{apiErrorMessage(history.error)}</p>}
    {history.isPending && <p>Loading execution history...</p>}
    {executionHistorySchema.safeParse(history.data).success && executionHistorySchema.parse(history.data).map(item => <button key={item.id} disabled={busy || pending} onClick={() => void load(item.id)}>{item.preview.repository} / {item.state.replaceAll("_", " ")} / {item.id.slice(0, 8)}</button>)}
  </section>;
}
