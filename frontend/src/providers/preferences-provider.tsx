"use client";

import { createContext, useContext, useEffect, useState, useSyncExternalStore } from "react";
type Preferences = { theme: "dark" | "light"; reducedMotion: boolean };
const defaults: Preferences = { theme: "dark", reducedMotion: false };
class PreferenceStore {
  private state = defaults;
  private listeners = new Set<() => void>();
  getSnapshot = () => this.state;
  getServerSnapshot = () => defaults;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  load = () => {
    try {
      const value = JSON.parse(localStorage.getItem("codemate-preferences") || "null");
      if (value && ["dark", "light"].includes(value.theme) && typeof value.reducedMotion === "boolean") {
        this.state = { theme: value.theme, reducedMotion: value.reducedMotion };
        this.listeners.forEach(listener => listener());
      }
    } catch { /* Preferences are optional when storage is blocked. */ }
  };
  set(value: Preferences) {
    this.state = value; this.listeners.forEach(listener => listener());
    try { localStorage.setItem("codemate-preferences", JSON.stringify(value)); } catch { /* In-memory preference still works. */ }
  }
}
const Context = createContext<PreferenceStore | null>(null);
export function PreferencesProvider({ children }: { children: React.ReactNode }) {
  const [store] = useState(() => new PreferenceStore());
  const prefs = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot);
  useEffect(() => { store.load(); window.addEventListener("storage", store.load); return () => window.removeEventListener("storage", store.load); }, [store]);
  useEffect(() => { document.documentElement.dataset.theme = prefs.theme; document.documentElement.dataset.reducedMotion = String(prefs.reducedMotion); }, [prefs]);
  return <Context.Provider value={store}>{children}</Context.Provider>;
}
export function usePreferences() {
  const store = useContext(Context); if (!store) throw new Error("PreferencesProvider is missing.");
  const preferences = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getServerSnapshot);
  return { ...preferences, setPreferences: (value: Preferences) => store.set(value) };
}
