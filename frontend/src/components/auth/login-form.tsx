"use client";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, LoaderCircle, ShieldCheck } from "lucide-react";
import { loginSchema, type LoginValues } from "@/lib/auth/validation";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import { useAuth } from "@/providers/auth-provider";
import { FormField, PasswordField } from "./form-fields";
export function LoginForm() {
  const { session, notice, error: sessionError } = useAuth(); const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginValues>({ resolver: zodResolver(loginSchema) });
  const submit = handleSubmit(async values => {
    setError(null);
    try { await session.login(values); router.replace("/dashboard"); }
    catch (failure) { setError(failure instanceof ApiError && failure.status === 401 ? "Email or password is incorrect, or the account is unavailable." : apiErrorMessage(failure)); }
  });
  return <div className="auth-form-content"><span className="eyebrow">WELCOME BACK</span><h1>Sign in to CodeMate</h1><p className="muted">Your workspace is one sign-in away.</p>{notice && <div className="notice" role="status">{notice}</div>}{sessionError && <div className="notice warning">Session check unavailable. You can retry signing in.</div>}{error && <div className="notice danger" role="alert">{error}</div>}<form noValidate onSubmit={submit}><fieldset disabled={isSubmitting}><FormField label="Email address" field={register("email")} type="email" autoComplete="email" placeholder="you@example.com" error={errors.email?.message} /><PasswordField label="Password" field={register("password")} autoComplete="current-password" error={errors.password?.message} /><button className="button primary wide" type="submit">{isSubmitting ? <><LoaderCircle className="spin" size={18} /> Signing in…</> : <>Sign in <ArrowRight size={18} /></>}</button></fieldset></form><p className="auth-switch">New here? <Link href="/register">Create an account</Link></p><p className="secure-note"><ShieldCheck size={15} /> Passwords are verified by your CodeMate backend.</p></div>;
}
