import { Suspense } from "react";
import { CICDPage } from "@/components/github/cicd";
export default function Page() { return <Suspense fallback={<p>Loading GitHub workspace…</p>}><CICDPage/></Suspense>; }
