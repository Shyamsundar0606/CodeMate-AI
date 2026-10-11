import { Suspense } from "react";
import { RepositoryDetail } from "@/components/github/detail";
export default function Page() { return <Suspense fallback={<p>Loading GitHub workspace…</p>}><RepositoryDetail/></Suspense>; }
