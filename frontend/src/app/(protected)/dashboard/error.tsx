"use client";
import { ErrorState } from "@/components/ui/page-state";
export default function DashboardError({ reset }: { reset: () => void }) { return <ErrorState title="Workspace unavailable" message="This page could not be displayed. Please try again." retry={reset} />; }
