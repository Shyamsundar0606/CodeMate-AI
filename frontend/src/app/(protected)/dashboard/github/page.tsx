import { Suspense } from "react";
import { GitHubConnectionPage } from "@/components/github/connection";
export default function Page() { return <Suspense fallback={<p>Loading GitHub workspace…</p>}><GitHubConnectionPage/></Suspense>; }
