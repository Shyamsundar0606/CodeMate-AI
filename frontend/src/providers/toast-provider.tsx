"use client";
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { X } from "lucide-react";
type Toast = { id: number; message: string; warning: boolean };
const Context = createContext<(message: string, warning?: boolean) => void>(() => {});
function ToastItem({ toast, dismiss }: { toast: Toast; dismiss: (id: number) => void }) {
  useEffect(() => { const timer = setTimeout(() => dismiss(toast.id), 7000); return () => clearTimeout(timer); }, [toast.id, dismiss]);
  return <div className={`toast ${toast.warning ? "warning" : ""}`} role="status"><span>{toast.message}</span><button aria-label="Dismiss notification" onClick={() => dismiss(toast.id)}><X size={16} /></button></div>;
}
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const notify = useCallback((message: string, warning = false) => setToasts(previous => [...previous.slice(-2), { id: Date.now() + Math.random(), message, warning }]), []);
  const dismiss = useCallback((id: number) => setToasts(previous => previous.filter(toast => toast.id !== id)), []);
  return <Context.Provider value={notify}>{children}<div className="toast-region" aria-live="polite">{toasts.map(toast => <ToastItem key={toast.id} toast={toast} dismiss={dismiss} />)}</div></Context.Provider>;
}
export const useToast = () => useContext(Context);
