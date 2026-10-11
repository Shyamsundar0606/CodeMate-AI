"use client";
import { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "./auth-provider";
import { PreferencesProvider } from "./preferences-provider";
import { ToastProvider } from "./toast-provider";
export function AppProviders({ children }: { children: React.ReactNode }) {
  const [queries] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 30000, refetchOnWindowFocus: false } } }));
  return <QueryClientProvider client={queries}><PreferencesProvider><ToastProvider><AuthProvider>{children}</AuthProvider></ToastProvider></PreferencesProvider></QueryClientProvider>;
}
