"use client";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/providers/auth-provider";
import { userPageSchema } from "@/types/api";
import { ApiError, apiErrorMessage } from "@/lib/api/client";
import { ErrorState, LoadingState } from "@/components/ui/page-state";
export function AdminUsers() {
  const { user, session } = useAuth(); const [offset, setOffset] = useState(0); const limit = 10;
  const query = useQuery({ queryKey: ["users", user?.id, offset], queryFn: () => session.get(`/api/v1/users?offset=${offset}&limit=${limit}`, userPageSchema), enabled: user?.role === "ADMIN" });
  if (user?.role !== "ADMIN" || (query.error instanceof ApiError && query.error.status === 403)) return <ErrorState title="Access restricted" message="This directory requires an administrator account. The API enforces access permissions." />;
  if (query.isPending) return <LoadingState message="Loading user directory…" />;
  if (query.isError) return <ErrorState title="Directory unavailable" message={apiErrorMessage(query.error)} retry={() => void query.refetch()} />;
  const { items, total } = query.data;
  return <><div className="page-heading"><div><span className="eyebrow">ADMINISTRATION</span><h1>User directory</h1><p>Read-only account directory. Permissions are enforced by the backend.</p></div><span className="badge">{total} ACCOUNTS</span></div><section className="card directory-card"><div className="table-scroll"><table><caption className="sr-only">Registered users</caption><thead><tr><th>Username</th><th>Email</th><th>Role</th><th>Status</th><th>Created</th></tr></thead><tbody>{items.map(item => <tr key={item.id}><td>{item.username}</td><td>{item.email}</td><td><span className="badge">{item.role}</span></td><td>{item.is_active ? "Active" : "Inactive"}</td><td>{new Date(item.created_at).toLocaleDateString()}</td></tr>)}</tbody></table></div>{items.length === 0 && <p className="empty-state">No accounts on this page.</p>}<div className="pagination"><span className="small muted">{total ? `${offset + 1}–${offset + items.length}` : "0"} of {total}</span><div><button className="button secondary" disabled={offset === 0 || query.isFetching} onClick={() => setOffset(Math.max(0, offset - limit))}>Previous</button><button className="button secondary" disabled={offset + limit >= total || query.isFetching} onClick={() => setOffset(offset + limit)}>Next</button></div></div></section></>;
}
