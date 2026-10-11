import { csrfSchema, tokenSchema, userSchema } from "@/types/api";
import { ApiClient } from "./client";

export type LoginInput = { email: string; password: string };
export type RegisterInput = LoginInput & { username: string };
export const authHeaders = { "X-CodeMate-Request": "1" };

export function registerAccount(api: ApiClient, input: RegisterInput) {
  // Explicit allowlist: confirmation fields and roles never reach registration.
  const body = { username: input.username, email: input.email, password: input.password };
  return api.request("/api/v1/auth/register", { method: "POST", headers: authHeaders, body: JSON.stringify(body) }, userSchema);
}
export function loginAccount(api: ApiClient, input: LoginInput) {
  return api.request("/api/v1/auth/login", { method: "POST", headers: authHeaders, body: JSON.stringify(input) }, tokenSchema);
}
export function bootstrapCsrf(api: ApiClient) {
  return api.request("/api/v1/auth/csrf", { headers: authHeaders }, csrfSchema);
}
export function rotateSession(api: ApiClient, csrf: string) {
  return api.request("/api/v1/auth/refresh", { method: "POST", headers: { ...authHeaders, "X-CSRF-Token": csrf } }, tokenSchema);
}
export function revokeSession(api: ApiClient, csrf: string) {
  return api.request<void>("/api/v1/auth/logout", { method: "POST", headers: { ...authHeaders, "X-CSRF-Token": csrf } });
}
