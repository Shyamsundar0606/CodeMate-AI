import { z } from "zod";
export const capabilitiesSchema = z.object({ enabled: z.boolean(), stt_installed: z.boolean(), tts_installed: z.boolean(), ollama_available: z.boolean(), max_recording_seconds: z.number(), max_upload_bytes: z.number(), message: z.string().max(262144) });
export const targetSchema = z.object({ owner: z.string().max(262144), repo: z.string().max(262144), installation_id: z.number(), workflow_run_id: z.number(), status: z.string().max(262144), conclusion: z.string().max(262144).nullable(), connection_id: z.string().max(262144).uuid() });
export const replySchema = z.object({ session_id: z.string().max(262144).uuid(), turn_id: z.string().max(262144).uuid(), intent: z.string().max(262144), message: z.string().max(262144), route: z.string().max(262144).nullable(), confirmation_required: z.boolean(), action_id: z.string().max(262144).uuid().nullable(), target: targetSchema.nullable(), choices: z.array(z.string().max(262144)).max(100) });
export const actionSchema = z.object({ message: z.string().max(262144), route: z.string().max(262144).nullable() });
export const transcriptionSchema = z.object({ text: z.string().max(262144), language: z.string().max(262144) });
export type VoiceReply = z.infer<typeof replySchema>;
export function safeVoiceRoute(route: string | null) {
  if (!route) return null;
  const staticRoutes = ["/dashboard/automation", "/dashboard", "/dashboard/github", "/dashboard/repositories", "/dashboard/cicd", "/dashboard/ai", "/dashboard/profile", "/dashboard/settings"];
  if (staticRoutes.includes(route)) return route;
  if (/^\/dashboard\/ai\/investigations\/[0-9a-f-]{36}$/.test(route)) return route;
  try {
    const url = new URL(route, "http://codemate.invalid");
    if (url.origin !== "http://codemate.invalid" || url.hash || !route.startsWith("/dashboard/")) return null;
    if (/^\/dashboard\/repositories\/[A-Za-z0-9-]+\/[A-Za-z0-9_.-]+$/.test(url.pathname) && [...url.searchParams.keys()].join() === "installation" && /^[1-9]\d*$/.test(url.searchParams.get("installation") || "")) return route;
    if (/^\/dashboard\/cicd\/runs\/[1-9]\d*$/.test(url.pathname) && [...url.searchParams.keys()].sort().join() === "installation,owner,repo" && /^[A-Za-z0-9-]+$/.test(url.searchParams.get("owner") || "") && /^[A-Za-z0-9_.-]+$/.test(url.searchParams.get("repo") || "") && /^[1-9]\d*$/.test(url.searchParams.get("installation") || "")) return route;
  } catch { /* Untrusted routes are rejected. */ }
  return null;
}
