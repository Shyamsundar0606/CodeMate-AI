import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "@/providers/auth-provider";
const claim = z.object({ evidence_id: z.string().max(262144), quote: z.string().max(262144) });
const finding = z.object({
  id: z.string().max(262144), title: z.string().max(262144), description: z.string().max(262144),
  severity: z.enum(["INFO", "LOW", "MEDIUM", "HIGH"]), confidence: z.enum(["LOW", "MEDIUM", "HIGH"]),
  evidence: z.array(claim).max(100), root_cause_hypothesis: z.string().max(262144), suggested_fix: z.string().max(262144),
  verification_steps: z.array(z.string().max(262144)).max(100),
});
const evidence = z.object({
  id: z.string().max(262144), workflow_run_id: z.number(), job_id: z.number().nullable(), step: z.string().max(262144).nullable(),
  source: z.enum(["job_log", "job_metadata", "run_metadata"]), excerpt: z.string().max(262144),
  line_start: z.number().nullable(), line_end: z.number().nullable(), timestamp: z.string().max(262144).nullable(),
  redacted: z.boolean(), truncated: z.boolean(),
});
export const investigationSchema = z.object({
  id: z.string().max(262144).uuid(), owner: z.string().max(262144), repo: z.string().max(262144), workflow_run_id: z.number(),
  installation_id: z.number(), status: z.enum(["queued", "running", "completed", "failed", "cancelled"]),
  stage: z.string().max(262144), attempts: z.number(), max_attempts: z.number(),
  created_at: z.string().max(262144), started_at: z.string().max(262144).nullable(), completed_at: z.string().max(262144).nullable(),
  error_code: z.string().max(262144).nullable(), error_message: z.string().max(262144).nullable(),
  report: z.object({
    summary: z.string().max(262144), failure_category: z.string().max(262144), findings: z.array(finding).max(100),
    recommended_actions: z.array(z.string().max(262144)).max(100), limitations: z.array(z.string().max(262144)).max(100),
    workflow_name: z.string().max(262144).nullable(), commit_sha: z.string().max(262144), branch: z.string().max(262144).nullable(),
    run_conclusion: z.string().max(262144).nullable(), analyzed_job_ids: z.array(z.number()).max(100),
    model_name: z.string().max(262144).nullable(), evidence_completeness: z.enum(["complete", "partial", "missing"]),
    evidence: z.array(evidence).max(100),
  }).nullable(),
});
export const aiStatusSchema = z.object({
  available: z.boolean(), model_available: z.boolean(), selected_model: z.string().max(262144), message: z.string().max(262144),
});
export const historySchema = z.object({
  items: z.array(investigationSchema).max(100), page: z.number(), has_next: z.boolean(),
  completed_count: z.number(), failed_count: z.number(),
});
export type Investigation = z.infer<typeof investigationSchema>;
export type RunContext = { installation_id: number; owner: string; repo: string; workflow_run_id: number };
export function useAI<T>(path: string, schema: z.ZodType<T>, poll = false) {
  const { user, status, session } = useAuth();
  const [started] = useState(() => Date.now());
  return useQuery({
    queryKey: ["ai", user?.id, path],
    queryFn: ({ signal }) => session.get(path, schema, signal),
    enabled: status === "authenticated", retry: false, gcTime: 60000,
    refetchOnWindowFocus: false,
    refetchInterval: query => poll && Date.now() - started < 600000 &&
      ["queued", "running"].includes((query.state.data as Investigation | undefined)?.status || "")
      ? 2000 : false,
  });
}
