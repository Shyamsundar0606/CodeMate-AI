"use client";
import { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import type { UseFormRegisterReturn } from "react-hook-form";
type Props = { label: string; field: UseFormRegisterReturn; error?: string; autoComplete: string; placeholder?: string; type?: string };
export function FormField({ label, field, error, autoComplete, placeholder, type = "text" }: Props) {
  return <div className="form-field"><label htmlFor={field.name}>{label}</label><input id={field.name} {...field} type={type} autoComplete={autoComplete} placeholder={placeholder} aria-invalid={!!error} aria-describedby={error ? `${field.name}-error` : undefined} />{error && <p className="field-error" id={`${field.name}-error`}>{error}</p>}</div>;
}
export function PasswordField({ label, field, error, autoComplete }: Props) {
  const [visible, setVisible] = useState(false);
  return <div className="form-field"><label htmlFor={field.name}>{label}</label><div className="password-field"><input id={field.name} {...field} type={visible ? "text" : "password"} autoComplete={autoComplete} aria-invalid={!!error} aria-describedby={error ? `${field.name}-error` : undefined} /><button type="button" className="password-toggle" aria-label={`${visible ? "Hide" : "Show"} ${label.toLowerCase()}`} aria-pressed={visible} onClick={() => setVisible(value => !value)}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button></div>{error && <p className="field-error" id={`${field.name}-error`}>{error}</p>}</div>;
}
