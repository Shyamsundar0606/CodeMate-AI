import { Suspense } from "react";
import { RepositoryExplorer } from "@/components/github/repositories";
export default function Page() { return <Suspense fallback={<p>Loading GitHub workspace…</p>}><RepositoryExplorer/></Suspense>; }
