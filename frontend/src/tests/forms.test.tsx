import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginForm } from "@/components/auth/login-form";
import { RegisterForm } from "@/components/auth/register-form";
import { ApiError } from "@/lib/api/client";
import { registerSchema } from "@/lib/auth/validation";
import { response, user, credentials } from "./fixtures";
const { login, push, replace } = vi.hoisted(() => ({ login: vi.fn(), push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ push, replace }) }));
vi.mock("@/providers/auth-provider", () => ({ useAuth: () => ({ session: { login }, notice: null, error: null }) }));
beforeEach(() => { login.mockReset(); push.mockReset(); replace.mockReset(); });
async function fillRegistration() { const keyboard = userEvent.setup(); await keyboard.type(screen.getByLabelText("Username"), "engineer"); await keyboard.type(screen.getByLabelText("Email address"), credentials.email); await keyboard.type(screen.getByLabelText("Password", { exact: true }), credentials.password); await keyboard.type(screen.getByLabelText("Confirm password"), credentials.password); return keyboard; }
it("validates empty registration without contacting the backend", async () => {
 const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher); render(<RegisterForm />);
 await userEvent.click(screen.getByRole("button", { name: "Create account" }));
 expect(await screen.findByText("Use at least 3 characters.")).toBeVisible(); expect(fetcher).not.toHaveBeenCalled();
});
it("enforces password length, categories, username syntax and confirmation", () => {
 const valid = { username: "engineer", ...credentials, confirmPassword: credentials.password };
 expect(registerSchema.safeParse(valid).success).toBe(true);
 for (const patch of [{ password: "short" }, { password: "onlylowercasepassword", confirmPassword: "onlylowercasepassword" }, { username: "Bad-User" }, { confirmPassword: "different" }]) expect(registerSchema.safeParse({ ...valid, ...patch }).success).toBe(false);
});
it("keeps registration on the page and shows a duplicate-account error", async () => {
 vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response({}, 409))); render(<RegisterForm />); const keyboard = await fillRegistration(); await keyboard.click(screen.getByRole("button", { name: "Create account" }));
 expect(await screen.findByRole("alert")).toHaveTextContent("already registered"); expect(push).not.toHaveBeenCalled();
});
it("waits for confirmed registration and disables the form while submitting", async () => {
 let resolve!: (value: Response) => void; vi.stubGlobal("fetch", vi.fn(() => new Promise<Response>(done => { resolve = done; })));
 render(<RegisterForm />); const keyboard = await fillRegistration(); await keyboard.click(screen.getByRole("button", { name: "Create account" }));
 expect(screen.getByRole("button", { name: "Creating account…" })).toBeDisabled(); expect(push).not.toHaveBeenCalled(); resolve(response(user, 201)); await waitFor(() => expect(push).toHaveBeenCalledWith("/login"));
});
it("logs in with normalized email and navigates only after success", async () => {
 login.mockResolvedValue(undefined); render(<LoginForm />); const keyboard = userEvent.setup();
 await keyboard.type(screen.getByLabelText("Email address"), "ENGINEER@example.com"); await keyboard.type(screen.getByLabelText("Password"), credentials.password); await keyboard.click(screen.getByRole("button", { name: "Sign in" }));
 await waitFor(() => expect(replace).toHaveBeenCalledWith("/dashboard")); expect(login).toHaveBeenCalledWith(credentials);
});
it.each([[401, "incorrect"], [429, "Too many"]])("displays login failure %s without navigating", async (status, message) => {
 login.mockRejectedValue(new ApiError(status === 429 ? "Too many sign-in attempts. Please wait." : "expired", status)); render(<LoginForm />); const keyboard = userEvent.setup();
 await keyboard.type(screen.getByLabelText("Email address"), credentials.email); await keyboard.type(screen.getByLabelText("Password"), credentials.password); await keyboard.click(screen.getByRole("button", { name: "Sign in" }));
 expect(await screen.findByRole("alert")).toHaveTextContent(message); expect(replace).not.toHaveBeenCalled();
});
it("offers an accessible password visibility control", async () => {
 render(<LoginForm />); const field = screen.getByLabelText("Password"); expect(field).toHaveAttribute("type", "password");
 await userEvent.click(screen.getByRole("button", { name: "Show password" })); expect(field).toHaveAttribute("type", "text"); expect(screen.getByRole("button", { name: "Hide password" })).toHaveAttribute("aria-pressed", "true");
});
