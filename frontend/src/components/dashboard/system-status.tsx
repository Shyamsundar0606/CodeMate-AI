"use client";
import { RefreshCw, Server, Database } from "lucide-react";
import { useSystemStatus } from "@/hooks/use-system-status";
export function SystemStatus() {
  const { backend, database, refresh } = useSystemStatus();
  const busy = backend.isFetching || database.isFetching;
  return <section className="card system-status" aria-labelledby="system-title"><div className="card-heading"><div><span className="eyebrow">LIVE CONNECTIVITY</span><h2 id="system-title">System status</h2></div><button className="icon-button" aria-label="Refresh system status" disabled={busy} onClick={() => void refresh()}><RefreshCw size={18} className={busy ? "spin" : ""} /></button></div><div className="status-grid">{[{ name: "Backend API", icon: Server, query: backend }, { name: "PostgreSQL", icon: Database, query: database }].map(({ name, icon: Icon, query }) => <div className="status-item" key={name}><Icon size={20} /><div><strong>{name}</strong><span>{query.dataUpdatedAt ? `Last success: ${new Date(query.dataUpdatedAt).toLocaleTimeString()}` : "No successful check yet"}</span></div><span className={`status-pill ${query.isPending ? "pending" : query.isError ? "offline" : "online"}`}>{query.isPending ? "Checking" : query.isError ? "Unavailable" : "Online"}</span></div>)}</div><p className="small muted">Public service checks run every minute. Account authorization is verified separately.</p></section>;
}
