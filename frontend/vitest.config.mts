import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
export default defineConfig({ resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } }, test: { environment: "jsdom", globals: true, setupFiles: ["./src/tests/setup.ts"], include: ["src/tests/**/*.test.{ts,tsx}"], restoreMocks: true } });
