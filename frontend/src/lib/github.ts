import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/providers/auth-provider";
export const connectionSchema = z.object({
  configured: z.boolean(),
  status: z.enum(["disconnected", "connected", "reauthorization_required"]),
  github_login: z.string().max(262144).nullable(),
  github_display_name: z.string().max(262144).nullable(),
  github_avatar_url: z.string().max(262144).nullable(),
  granted_permissions: z.record(z.string().max(180), z.string().max(262144)),
  last_verified_at: z.string().max(262144).nullable(),
  install_url: z.string().max(262144).nullable(),
});
export const installationSchema = z.object({
  id: z.number().positive(),
  account: z.string().max(262144),
  repository_selection: z.enum(["all", "selected"]),
  permissions: z.record(z.string().max(180), z.string().max(262144)),
  suspended: z.boolean(),
});
export const repositorySchema = z.object({
  id: z.number().positive(),
  name: z.string().max(262144),
  full_name: z.string().max(262144),
  owner: z.string().max(262144),
  description: z.string().max(262144).nullable(),
  private: z.boolean(),
  default_branch: z.string().max(262144).nullable(),
  language: z.string().max(262144).nullable(),
  stars: z.number(),
  forks: z.number(),
  fork: z.boolean(),
  updated_at: z.string().max(262144),
  pushed_at: z.string().max(262144).nullable(),
  html_url: z.string().max(262144),
});
export const branchSchema = z.object({
  name: z.string().max(262144),
  sha: z.string().max(262144),
  protected: z.boolean(),
});
export const commitSchema = z.object({
  sha: z.string().max(262144),
  short_sha: z.string().max(262144),
  message: z.string().max(262144),
  author: z.string().max(262144).nullable(),
  timestamp: z.string().max(262144).nullable(),
  html_url: z.string().max(262144),
});
export const pullSchema = z.object({
  number: z.number(),
  title: z.string().max(262144),
  state: z.string().max(262144),
  author: z.string().max(262144).nullable(),
  created_at: z.string().max(262144),
  updated_at: z.string().max(262144),
  base: z.string().max(262144),
  head: z.string().max(262144),
  draft: z.boolean(),
  html_url: z.string().max(262144),
});
export const issueSchema = z.object({
  number: z.number(),
  title: z.string().max(262144),
  state: z.string().max(262144),
  author: z.string().max(262144).nullable(),
  created_at: z.string().max(262144),
  updated_at: z.string().max(262144),
  labels: z.array(z.string().max(262144)).max(100),
  html_url: z.string().max(262144),
});
export const workflowSchema = z.object({
  id: z.number(),
  name: z.string().max(262144),
  path: z.string().max(262144),
  state: z.string().max(262144),
  html_url: z.string().max(262144),
});
export const runSchema = z.object({
  id: z.number(),
  name: z.string().max(262144).nullable(),
  run_number: z.number(),
  branch: z.string().max(262144).nullable(),
  sha: z.string().max(262144),
  event: z.string().max(262144),
  status: z.string().max(262144),
  conclusion: z.string().max(262144).nullable(),
  created_at: z.string().max(262144),
  updated_at: z.string().max(262144),
  started_at: z.string().max(262144).nullable(),
  duration_seconds: z.number().nullable(),
  html_url: z.string().max(262144),
});
export const jobSchema = z.object({
  id: z.number(),
  run_id: z.number(),
  name: z.string().max(262144),
  status: z.string().max(262144),
  conclusion: z.string().max(262144).nullable(),
  started_at: z.string().max(262144).nullable(),
  completed_at: z.string().max(262144).nullable(),
  html_url: z.string().max(262144),
  steps: z.array(
    z.object({
      number: z.number(),
      name: z.string().max(262144),
      status: z.string().max(262144),
      conclusion: z.string().max(262144).nullable(),
    }),
  ).max(100),
});
export const logSchema = z.object({
  job_id: z.number(),
  content: z.string().max(262144),
  byte_limit: z.number(),
  truncated: z.boolean(),
  redacted: z.boolean(),
  warning: z.string().max(262144),
  fetched_at: z.string().max(262144),
});
export const connectSchema = z.object({ authorization_url: z.string().max(262144) });
export const disconnectSchema = z.object({
  disconnected: z.boolean(),
  remote_revoked: z.boolean(),
  message: z.string().max(262144),
});
export const pageSchema = <T extends z.ZodTypeAny>(item: T) =>
  z.object({
    items: z.array(item).max(100),
    page: z.number(),
    per_page: z.number(),
    has_next: z.boolean(),
    total: z.number().nullable(),
    scope: z.string().max(262144),
    fetched_at: z.string().max(262144),
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
