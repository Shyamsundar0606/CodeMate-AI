import { expect, it, vi } from "vitest";
import { z } from "zod";
import { ApiClient, ApiError } from "@/lib/api/client";
import { checkShape, InputLimitError, JSON_BYTES, readBounded } from "@/lib/api/limits";
import { pageSchema, repositorySchema } from "@/lib/github";
import { loginSchema, registerSchema } from "@/lib/auth/validation";

it("bounds streamed bytes without trusting Content-Length and cancels the reader", async () => {
  const cancel = vi.fn();
  const stream = new ReadableStream({ start(controller) { controller.enqueue(new Uint8Array(9)); }, cancel });
  await expect(readBounded(new Response(stream), 8)).rejects.toBeInstanceOf(InputLimitError);
  expect(cancel).toHaveBeenCalledOnce();
});

it("rejects declared oversize before reading and accepts the exact byte boundary", async () => {
  await expect(readBounded(new Response("x", { headers: { "content-length": "9" } }), 8)).rejects.toBeInstanceOf(InputLimitError);
  expect(await readBounded(new Response("12345678"), 8)).toHaveLength(8);
});

it("rejects oversized collections, records, keys, strings and nesting before schema traversal", () => {
  const deep: unknown = Array.from({ length: 34 }).reduce<unknown>(value => ({ value }), null);
  for (const value of [Array(1001).fill(null), Object.fromEntries(Array.from({ length: 513 }, (_, i) => [i, null])), { ["x".repeat(1025)]: null }, "x".repeat(262145), deep]) {
    expect(() => checkShape(value)).toThrow(InputLimitError);
  }
  expect(() => checkShape(Array(1000).fill(null))).not.toThrow();
  expect(() => checkShape(Array.from({ length: 21 }, () => Array(1000).fill(null)))).toThrow(InputLimitError);
});

it("never invokes Zod for a JSON tree exceeding the collection cap", async () => {
  const schema = z.array(z.string());
  const parser = vi.spyOn(schema, "safeParse");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(Array(1001).fill("x")))));
  await expect(new ApiClient().request("/test", {}, schema)).rejects.toMatchObject({ kind: "protocol" });
  expect(parser).not.toHaveBeenCalled();
});

it("bounds successful and error responses and keeps diagnostics sanitized", async () => {
  for (const status of [200, 503]) {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("x", { status, headers: { "content-length": String(JSON_BYTES + 1) } })));
    await expect(new ApiClient().request("/api/v1/automation/test")).rejects.toBeInstanceOf(ApiError);
  }
});

it("enforces API page limits and bounded form inputs after the Zod 4 migration", () => {
  expect(pageSchema(repositorySchema).safeParse({ items: Array(101).fill({}), page: 1, per_page: 100, has_next: false, total: 101, scope: "test", fetched_at: "now" }).success).toBe(false);
  expect(loginSchema.safeParse({ email: "x".repeat(255), password: "password" }).success).toBe(false);
  expect(registerSchema.safeParse({ username: "engineer", email: "user@example.com", password: "ValidPassword123!", confirmPassword: "x".repeat(129) }).success).toBe(false);
});
