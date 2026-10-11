"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { ErrorState, LoadingState } from "@/components/ui/page-state";
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status, session, error } = useAuth(); const router = useRouter(); const [retrying, setRetrying] = useState(false);
  useEffect(() => { if (status === "anonymous") router.replace("/login"); }, [status, router]);
  if (status === "unavailable" && !retrying) return <div className="guard-page"><ErrorState title="Could not verify your session" message={error || "The API is unavailable. Your protected workspace stays hidden until verification succeeds."} retry={() => { setRetrying(true); void session.restore().finally(() => setRetrying(false)); }} /></div>;
  if (status !== "authenticated" || retrying) return <LoadingState />;
  return children;
}
