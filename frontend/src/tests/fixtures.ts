import type { User } from "@/types/api";
export const user: User = { id: "3c337168-8a43-4f3e-bbaf-cf055ec41109", username: "engineer", email: "engineer@example.com", role: "USER" as const, is_active: true, created_at: "2026-10-01T09:00:00Z", updated_at: "2026-10-01T09:00:00Z" };
export const csrf = "a".repeat(64);
export const tokens = { access_token: "private-access-token", token_type: "bearer", expires_in: 900, csrf_token: csrf };
export const credentials = { email: user.email, password: "StrongPassword123!" };
export function response(data: unknown, status = 200) { return new Response(status === 204 ? null : JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } }); }
