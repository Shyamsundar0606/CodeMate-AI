import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  distDir: process.env.CODEMATE_E2E === "1" ? ".next-e2e" : ".next",
  // Recompute build workers instead of reusing stale persisted CSS-worker artifacts.
  // Keep the existing cache on disk and leave development caching unchanged.
  experimental: { turbopackFileSystemCacheForBuild: false },
};
export default nextConfig;
