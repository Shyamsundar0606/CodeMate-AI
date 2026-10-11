"use client";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/lib/api/client";
import { healthSchema, readySchema } from "@/types/api";
export function useSystemStatus() {
  const backend = useQuery({ queryKey: ["health", "backend"], queryFn: () => apiClient.request("/health", {}, healthSchema), refetchInterval: 60000 });
  const database = useQuery({ queryKey: ["health", "database"], queryFn: () => apiClient.request("/health/ready", {}, readySchema), refetchInterval: 60000 });
  return { backend, database, refresh: () => Promise.all([backend.refetch(), database.refetch()]) };
}
