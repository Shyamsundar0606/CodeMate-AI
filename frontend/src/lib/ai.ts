import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useAuth } from "@/providers/auth-provider";
const claim = z.object({ evidence_id: z.string(), quote: z.string() });
const finding = z.object({
  id: z.string(), title: z.string(), description: z.string(),
  severity: z.enum(["INFO", "LOW", "MEDIUM", "HIGH"]), confidence: z.enum(["LOW", "MEDIUM", "HIGH"]),
  evidence: z.array(claim), root_cause_hypothesis: z.string(), suggested_fix: z.string(),
  verification_steps: z.array(z.string()),
});
const evidence = z.object({
  id: z.string(), workflow_run_id: z.number(), job_id: z.number().nullable(), step: z.string().nullable(),
  source: z.enum(["job_log", "job_metadata", "run_metadata"]), excerpt: z.string(),
  line_start: z.number().nullable(), line_end: z.number().nullable(), timestamp: z.string().nullable(),
  redacted: z.boolean(), truncated: z.boolean(),
});
export const investigationSchema = z.object({
  id: z.string().uuid(), owner: z.string(), repo: z.string(), workflow_run_id: z.number(),
  installation_id: z.number(), status: z.enum(["queued", "running", "completed", "failed", "cancelled"]),
  stage: z.string(), attempts: z.number(), max_attempts: z.number(),
  created_at: z.string(), started_at: z.string().nullable(), completed_at: z.string().nullable(),
  error_code: z.string().nullable(), error_message: z.string().nullable(),
  report: z.object({
    summary: z.string(), failure_category: z.string(), findings: z.array(finding),
    recommended_actions: z.array(z.string()), limitations: z.array(z.string()),
    workflow_name: z.string().nullable(), commit_sha: z.string(), branch: z.string().nullable(),
    run_conclusion: z.string().nullable(), analyzed_job_ids: z.array(z.number()),
    model_name: z.string().nullable(), evidence_completeness: z.enum(["complete", "partial", "missing"]),
    evidence: z.array(evidence),
  }).nullable(),
});
export const aiStatusSchema = z.object({
  available: z.boolean(), model_available: z.boolean(), selected_model: z.string(), message: z.string(),
});
export const historySchema = z.object({
  items: z.array(investigationSchema), page: z.number(), has_next: z.boolean(),
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
