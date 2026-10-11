"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/providers/auth-provider";
import { LoadingState } from "@/components/ui/page-state";
export function GuestGate({ children }: { children: React.ReactNode }) {
  const { status } = useAuth(); const router = useRouter();
  useEffect(() => { if (status === "authenticated") router.replace("/dashboard"); }, [status, router]);
  if (status === "restoring" || status === "authenticated") return <LoadingState />;
  return children;
}
