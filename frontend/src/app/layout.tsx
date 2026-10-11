import type { Metadata } from "next";
import { AppProviders } from "@/providers/app-providers";
import "./globals.css";
export const metadata: Metadata = { title: { default: "CodeMate AI | Developer workspace", template: "%s | CodeMate AI" }, description: "Your secure developer workspace. Clear system status and account management, with repository and AI integrations to come." };
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) { return <html lang="en"><body><AppProviders>{children}</AppProviders></body></html>; }
