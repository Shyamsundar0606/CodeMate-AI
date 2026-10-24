import { z } from "zod";

const profile = z.object({ id: z.literal("python_syntax"), argv: z.array(z.string().max(262144)).max(100), description: z.string().max(262144) });
export const runnerReadinessSchema = z.object({
  policy_version: z.literal("m10-readiness-v1"), state: z.literal("blocked"),
  checks: z.array(z.object({
    id: z.enum(["worker_identity", "launcher_boundary", "image_provenance", "hostile_isolation", "durable_recovery", "fixture_integration"]),
    status: z.enum(["not_implemented", "unverified"]), label: z.string().max(262144).max(80), reason: z.string().max(262144).max(240),
  }).strict()).length(6).refine(checks => new Set(checks.map(check => check.id)).size === 6, "Admission requirements must be distinct"),
}).strict();
export const sandboxCapabilitySchema = z.object({ execution_enabled: z.literal(false), verification: z.literal("unverified"), reasons: z.array(z.string().max(262144)).max(100), profiles: z.array(profile).max(100), readiness: runnerReadinessSchema });
export const executionPreviewSchema = z.object({
  id: z.string().max(262144).uuid(), state: z.enum(["awaiting_confirmation", "cancelled", "expired"]),
  binding_hash: z.string().max(262144), expires_at: z.string().max(262144), execution_enabled: z.literal(false),
  applied: z.literal(false), validation_status: z.literal("not_executed"), exit_code: z.null(),
  stdout: z.literal(""), stderr: z.literal(""), changed_manifest: z.array(z.unknown()).max(0),
  preview: z.object({ repository: z.string().max(262144), base_sha: z.string().max(262144), proposal_id: z.string().max(262144).uuid(),
    expected_manifest: z.array(z.object({ path: z.string().max(262144), before_sha256: z.string().max(262144), after_sha256: z.string().max(262144) })).max(100),
    patch_hash: z.string().max(262144), files: z.array(z.string().max(262144)).max(100), diff: z.string().max(262144), profiles: z.array(profile).max(100),
    isolation: z.object({ version: z.string().max(262144), image_digest: z.null(), network: z.literal("none"),
      memory_mib: z.number(), pids: z.number(), timeout_seconds: z.number(), output_bytes: z.number() }) }),
  audit: z.array(z.object({ event: z.string().max(262144), at: z.string().max(262144) })).max(100),
});
export const executionHistorySchema = z.array(executionPreviewSchema).max(100);
export type ExecutionPreview = z.infer<typeof executionPreviewSchema>;
