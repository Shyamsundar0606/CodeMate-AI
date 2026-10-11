"use client";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "@/providers/auth-provider";
export function Profile() {
  const { user } = useAuth();
  if (!user) return <p role="status">Profile unavailable.</p>;
  return <><div className="page-heading"><div><span className="eyebrow">YOUR ACCOUNT</span><h1>Profile</h1><p>Account details verified by the CodeMate API.</p></div></div><section className="card profile-card"><div className="profile-intro"><span className="avatar large-avatar">{user.username.slice(0, 2).toUpperCase()}</span><div><h2>{user.username}</h2><p>{user.email}</p></div><span className="status-pill online"><ShieldCheck size={14} /> {user.is_active ? "Active" : "Inactive"}</span></div><dl className="profile-details">{[["Username", user.username], ["Email address", user.email], ["Role", user.role], ["Account status", user.is_active ? "Active" : "Inactive"], ["Created", new Date(user.created_at).toLocaleDateString(undefined, { dateStyle: "long" })]].map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl><p className="small muted">Profile editing and password changes are not available in this milestone.</p></section></>;
}
