"use client";

import { createContext, useContext, useEffect, useState, useSyncExternalStore } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { SessionManager } from "@/lib/auth/session";

const AuthContext = createContext<SessionManager | null>(null);
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session] = useState(() => new SessionManager());
  const queries = useQueryClient();
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const schedule = () => {
      clearTimeout(timer);
      if (session.getSnapshot().status !== "authenticated") {
        queries.removeQueries({ queryKey: ["users"] });
        queries.removeQueries({ queryKey: ["github"] });
        return;
      }
      timer = setTimeout(() => { void session.restore(); }, session.renewalDelay());
    };
    const checkOnReturn = () => {
      if (document.visibilityState === "visible" && session.getSnapshot().status === "authenticated" && session.renewalDelay() <= 1000) void session.restore();
    };
    const unsubscribe = session.subscribe(schedule);
    session.connect(); void session.restore(); schedule();
    document.addEventListener("visibilitychange", checkOnReturn);
    return () => { clearTimeout(timer); unsubscribe(); document.removeEventListener("visibilitychange", checkOnReturn); session.disconnect(); };
  }, [session, queries]);
  return <AuthContext.Provider value={session}>{children}</AuthContext.Provider>;
}
export function useAuth() {
  const session = useContext(AuthContext);
  if (!session) throw new Error("AuthProvider is missing.");
  const state = useSyncExternalStore(session.subscribe, session.getSnapshot, session.getServerSnapshot);
  return { ...state, session };
}
