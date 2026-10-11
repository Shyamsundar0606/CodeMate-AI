"use client";
import { ErrorState } from "@/components/ui/page-state";
export default function ErrorPage({ reset }: { reset: () => void }) { return <main className="standalone-state"><ErrorState title="Something went wrong" message="This page could not be displayed. Please try again." retry={reset} /></main>; }
