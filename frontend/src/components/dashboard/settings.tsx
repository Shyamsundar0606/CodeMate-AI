"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { LogOut, Monitor, ShieldCheck } from "lucide-react";
import { usePreferences } from "@/providers/preferences-provider";
import { useAuth } from "@/providers/auth-provider";
import { useToast } from "@/providers/toast-provider";
export function SettingsPage() {
  const { theme, reducedMotion, setPreferences } = usePreferences(); const { session } = useAuth();
  const [busy, setBusy] = useState(false); const router = useRouter(); const notify = useToast();
  async function signOut() { setBusy(true); const revoked = await session.logout(); notify(revoked ? "Server session revoked." : "Signed out locally. Server revocation could not be confirmed.", !revoked); router.replace("/login"); }
  return <><div className="page-heading"><div><span className="eyebrow">MAKE IT YOURS</span><h1>Settings</h1><p>Preferences for this browser and your current session.</p></div></div><section className="card settings-card"><div className="card-heading"><h2><Monitor size={20} /> Appearance</h2><span className="badge">BROWSER ONLY</span></div><div className="setting-row"><div><label htmlFor="theme-select">Color theme</label><p>Saved locally in this browser, not to your account.</p></div><select id="theme-select" value={theme} onChange={event => setPreferences({ theme: event.target.value as "dark" | "light", reducedMotion })}><option value="dark">Dark</option><option value="light">Light</option></select></div><div className="setting-row"><div><label htmlFor="motion-toggle">Reduce motion</label><p>Minimize transitions. Your operating system preference is also respected.</p></div><input id="motion-toggle" type="checkbox" className="switch-input" checked={reducedMotion} onChange={event => setPreferences({ theme, reducedMotion: event.target.checked })} /></div></section><section className="card settings-card"><div className="card-heading"><h2><ShieldCheck size={20} /> Current session</h2></div><div className="setting-row"><div><strong>Sign out of this browser</strong><p>Revoke the active refresh session and clear your local authentication state.</p></div><button className="button secondary" disabled={busy} onClick={() => void signOut()}><LogOut size={16} />{busy ? "Signing out…" : "Sign out"}</button></div><p className="small muted">If the API is unavailable, local sign-out still clears this page. Server revocation will be reported as unconfirmed.</p></section></>;
}
