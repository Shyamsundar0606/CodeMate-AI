"use client";
import Link from "next/link";
import {useAuth} from "@/providers/auth-provider";
import {SystemStatus} from "./system-status";
import {GitHubOverview} from "@/components/github/overview";
export function Overview(){const {user}=useAuth();return <><div className="page-heading"><div><span className="eyebrow">WORKSPACE OVERVIEW</span><h1>Welcome back, {user?.username}.</h1><p>Explore your authorized repositories and development activity.</p></div><span className="badge accent-badge">DEVELOPER WORKSPACE</span></div><GitHubOverview/><SystemStatus/><section className="card github-notice"><h2>AI investigations</h2><p>Investigate failed workflows with local AI and inspect the supporting evidence. Model suggestions are unverified; execution remains disabled.</p><Link className="button secondary" href="/dashboard/ai">Open AI diagnostics</Link></section></>;}
