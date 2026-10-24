import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir: process.env.CODEMATE_E2E === "1" ? ".next-e2e" : ".next",
  // Recompute build workers instead of reusing stale persisted CSS-worker artifacts.
  // Keep the existing cache on disk and leave development caching unchanged.
  experimental: { turbopackFileSystemCacheForBuild: false },
  poweredByHeader: false,
  async headers() {
    const api = new URL(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000");
    if (!["http:", "https:"].includes(api.protocol) || api.username || api.password || api.search || api.hash) {
      throw new Error("Public API origin is invalid");
    }
    const development = process.env.NODE_ENV === "development";
    const policy = [
      "default-src 'self'", "base-uri 'self'", "frame-ancestors 'none'", "object-src 'none'",
      `script-src 'self' 'unsafe-inline'${development ? " 'unsafe-eval'" : ""}`,
      "style-src 'self' 'unsafe-inline'", "img-src 'self' data: blob:",
      "font-src 'self'", "media-src 'self' blob:", "worker-src 'self' blob:",
      `connect-src 'self' ${api.origin}${development ? " ws://localhost:* ws://127.0.0.1:*" : ""}`,
      "form-action 'self'",
    ].join("; ");
    return [{ source: "/:path*", headers: [
      { key: "Content-Security-Policy", value: policy },
      { key: "X-Content-Type-Options", value: "nosniff" },
      { key: "X-Frame-Options", value: "DENY" },
      { key: "Referrer-Policy", value: "no-referrer" },
      { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=(self)" },
    ] }];
  },
};
export default nextConfig;
