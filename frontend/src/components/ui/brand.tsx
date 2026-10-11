import Link from "next/link";
import { Terminal } from "lucide-react";
export function Brand({ compact = false }: { compact?: boolean }) {
  return <Link href="/" className="brand" aria-label="CodeMate AI home"><span className="brand-mark"><Terminal size={22} aria-hidden="true" /></span>{!compact && <span>CodeMate<span className="brand-ai"> AI</span></span>}</Link>;
}
