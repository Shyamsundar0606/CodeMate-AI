import { z } from "zod";

const profile = z.object({ id: z.literal("python_syntax"), argv: z.array(z.string()), description: z.string() });
export const sandboxCapabilitySchema = z.object({ execution_enabled: z.literal(false), verification: z.literal("unverified"), reasons: z.array(z.string()), profiles: z.array(profile) });
export const executionPreviewSchema = z.object({
  id: z.string().uuid(), state: z.enum(["awaiting_confirmation", "cancelled", "expired"]),
  binding_hash: z.string(), expires_at: z.string(), execution_enabled: z.literal(false),
  applied: z.literal(false), validation_status: z.literal("not_executed"), exit_code: z.null(),
  stdout: z.literal(""), stderr: z.literal(""), changed_manifest: z.array(z.unknown()).max(0),
  preview: z.object({ repository: z.string(), base_sha: z.string(), proposal_id: z.string().uuid(),
    expected_manifest: z.array(z.object({ path: z.string(), before_sha256: z.string(), after_sha256: z.string() })),
    patch_hash: z.string(), files: z.array(z.string()), diff: z.string(), profiles: z.array(profile),
    isolation: z.object({ version: z.string(), image_digest: z.null(), network: z.literal("none"),
      memory_mib: z.number(), pids: z.number(), timeout_seconds: z.number(), output_bytes: z.number() }) }),
  audit: z.array(z.object({ event: z.string(), at: z.string() })),
});
export const executionHistorySchema = z.array(executionPreviewSchema);
export type ExecutionPreview = z.infer<typeof executionPreviewSchema>;
