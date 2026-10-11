import { z } from "zod";

export const userSchema = z.object({
  id: z.string().uuid(), username: z.string(), email: z.string().email(),
  role: z.enum(["USER", "ADMIN"]), is_active: z.boolean(),
  created_at: z.string().datetime({ offset: true }), updated_at: z.string().datetime({ offset: true }),
});
export type User = z.infer<typeof userSchema>;
export const tokenSchema = z.object({
  access_token: z.string().min(1), token_type: z.literal("bearer"),
  expires_in: z.number().positive(), csrf_token: z.string().regex(/^[a-f0-9]{64}$/),
});
export type Tokens = z.infer<typeof tokenSchema>;
export const csrfSchema = z.object({ csrf_token: z.string().regex(/^[a-f0-9]{64}$/) });
export const userPageSchema = z.object({ items: z.array(userSchema), total: z.number().int().nonnegative(), offset: z.number().int(), limit: z.number().int() });
export type UserPage = z.infer<typeof userPageSchema>;
export const healthSchema = z.object({ status: z.literal("ok"), service: z.string(), version: z.string() });
export const readySchema = z.object({ status: z.literal("ok"), database: z.literal("ready") });
