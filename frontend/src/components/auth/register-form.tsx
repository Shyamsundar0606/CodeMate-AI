"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, LoaderCircle } from "lucide-react";
import { registerSchema, type RegisterValues } from "@/lib/auth/validation";
import { apiClient, apiErrorMessage } from "@/lib/api/client";
import { registerAccount } from "@/lib/api/auth";
import { useToast } from "@/providers/toast-provider";
import { FormField, PasswordField } from "./form-fields";
export function RegisterForm() {
  const router = useRouter(); const notify = useToast(); const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<RegisterValues>({ resolver: zodResolver(registerSchema) });
  const submit = handleSubmit(async values => {
    setError(null);
    try { await registerAccount(apiClient, values); notify("Account created. Sign in to open your workspace."); router.push("/login"); }
    catch (failure) { setError(apiErrorMessage(failure)); }
  });
  return <div className="auth-form-content"><span className="eyebrow">START SOMETHING GREAT</span><h1>Create your account</h1><p className="muted">A secure home for your development workflow.</p>{error && <div className="notice danger" role="alert">{error}</div>}<form noValidate onSubmit={submit}><fieldset disabled={isSubmitting}><FormField label="Username" field={register("username")} autoComplete="username" placeholder="your_username" error={errors.username?.message} /><FormField label="Email address" field={register("email")} type="email" autoComplete="email" placeholder="you@example.com" error={errors.email?.message} /><PasswordField label="Password" field={register("password")} autoComplete="new-password" error={errors.password?.message} /><p className="password-help">12–128 characters. Use at least 3 types: lowercase, uppercase, numbers, symbols.</p><PasswordField label="Confirm password" field={register("confirmPassword")} autoComplete="new-password" error={errors.confirmPassword?.message} /><button className="button primary wide" type="submit">{isSubmitting ? <><LoaderCircle className="spin" size={18} /> Creating account…</> : <>Create account <ArrowRight size={18} /></>}</button></fieldset></form><p className="auth-switch">Already have an account? <Link href="/login">Sign in</Link></p><p className="secure-note">New accounts receive the USER role. No external services required.</p></div>;
}
