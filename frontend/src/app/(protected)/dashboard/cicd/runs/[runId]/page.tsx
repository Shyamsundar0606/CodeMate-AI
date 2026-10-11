import { Suspense } from "react";
import { RunInvestigation } from "@/components/github/investigation";
export default function Page() { return <Suspense fallback={<p>Loading GitHub workspace…</p>}><RunInvestigation/></Suspense>; }
