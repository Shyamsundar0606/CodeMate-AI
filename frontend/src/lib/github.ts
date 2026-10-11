import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/providers/auth-provider";
export const connectionSchema = z.object({
  configured: z.boolean(),
  status: z.enum(["disconnected", "connected", "reauthorization_required"]),
  github_login: z.string().nullable(),
  github_display_name: z.string().nullable(),
  github_avatar_url: z.string().nullable(),
  granted_permissions: z.record(z.string()),
  last_verified_at: z.string().nullable(),
  install_url: z.string().nullable(),
});
export const installationSchema = z.object({
  id: z.number().positive(),
  account: z.string(),
  repository_selection: z.enum(["all", "selected"]),
  permissions: z.record(z.string()),
  suspended: z.boolean(),
});
export const repositorySchema = z.object({
  id: z.number().positive(),
  name: z.string(),
  full_name: z.string(),
  owner: z.string(),
  description: z.string().nullable(),
  private: z.boolean(),
  default_branch: z.string().nullable(),
  language: z.string().nullable(),
  stars: z.number(),
  forks: z.number(),
  fork: z.boolean(),
  updated_at: z.string(),
  pushed_at: z.string().nullable(),
  html_url: z.string(),
});
export const branchSchema = z.object({
  name: z.string(),
  sha: z.string(),
  protected: z.boolean(),
});
export const commitSchema = z.object({
  sha: z.string(),
  short_sha: z.string(),
  message: z.string(),
  author: z.string().nullable(),
  timestamp: z.string().nullable(),
  html_url: z.string(),
});
export const pullSchema = z.object({
  number: z.number(),
  title: z.string(),
  state: z.string(),
  author: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  base: z.string(),
  head: z.string(),
  draft: z.boolean(),
  html_url: z.string(),
});
export const issueSchema = z.object({
  number: z.number(),
  title: z.string(),
  state: z.string(),
  author: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  labels: z.array(z.string()),
  html_url: z.string(),
});
export const workflowSchema = z.object({
  id: z.number(),
  name: z.string(),
  path: z.string(),
  state: z.string(),
  html_url: z.string(),
});
export const runSchema = z.object({
  id: z.number(),
  name: z.string().nullable(),
  run_number: z.number(),
  branch: z.string().nullable(),
  sha: z.string(),
  event: z.string(),
  status: z.string(),
  conclusion: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  started_at: z.string().nullable(),
  duration_seconds: z.number().nullable(),
  html_url: z.string(),
});
export const jobSchema = z.object({
  id: z.number(),
  run_id: z.number(),
  name: z.string(),
  status: z.string(),
  conclusion: z.string().nullable(),
  started_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  html_url: z.string(),
  steps: z.array(
    z.object({
      number: z.number(),
      name: z.string(),
      status: z.string(),
      conclusion: z.string().nullable(),
    }),
  ),
});
export const logSchema = z.object({
  job_id: z.number(),
  content: z.string(),
  byte_limit: z.number(),
  truncated: z.boolean(),
  redacted: z.boolean(),
  warning: z.string(),
  fetched_at: z.string(),
});
export const connectSchema = z.object({ authorization_url: z.string() });
export const disconnectSchema = z.object({
  disconnected: z.boolean(),
  remote_revoked: z.boolean(),
  message: z.string(),
});
export const pageSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    items: z.array(item),
    page: z.number(),
    per_page: z.number(),
    has_next: z.boolean(),
    total: z.number().nullable(),
    scope: z.string(),
    fetched_at: z.string(),
  });
export function useGitHub<T>(
  path: string,
  schema: z.ZodType<T>,
  enabled = true,
) {
  const { user, status, session } = useAuth();
  return useQuery({
    queryKey: ["github", user?.id, path],
    queryFn: () => session.get(path, schema),
    enabled: enabled && status === "authenticated",
    retry: false,
    staleTime: 15000,
    gcTime: 60000,
    refetchOnWindowFocus: false,
  });
}
export function repoPath(owner: string, repo: string) {
  return `/api/v1/github/repositories/${encodeURIComponent(owner)}/${encodeURIComponent(repo)}`;
}
export function validRepo(owner: string, repo: string) {
  return (
    /^[A-Za-z0-9][A-Za-z0-9-]{0,38}$/.test(owner) &&
    /^[A-Za-z0-9_.-]{1,100}$/.test(repo) &&
    ![".", ".."].includes(repo)
  );
}
export function validId(value: string | null) {
  return (
    !!value &&
    /^[1-9][0-9]{0,15}$/.test(value) &&
    Number.isSafeInteger(Number(value))
  );
}
export function githubUrl(value: string) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" &&
      url.hostname === "github.com" &&
      !url.username &&
      !url.password &&
      !url.port
      ? value
      : "https://github.com";
  } catch {
    return "https://github.com";
  }
}
export function authorizationUrl(value: string) {
  const url = new URL(value);
  if (
    githubUrl(value) !== value ||
    url.pathname !== "/login/oauth/authorize" ||
    url.searchParams.get("code_challenge_method") !== "S256" ||
    !url.searchParams.get("state")
  )
    throw new Error("Invalid authorization destination.");
  return value;
}
export function runLabel(status: string, conclusion: string | null) {
  if (status !== "completed") return status.replaceAll("_", " ");
  return (conclusion || "completed").replaceAll("_", " ");
}
export function date(value: string | null) {
  return value ? new Date(value).toLocaleString() : "Unavailable";
}
export type Repository = z.infer<typeof repositorySchema>;
export type Run = z.infer<typeof runSchema>;
