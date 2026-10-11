import { z } from "zod";

const email = z.string().trim().email("Enter a valid email address.").transform(value => value.toLowerCase());
export const loginSchema = z.object({ email, password: z.string().min(1, "Enter your password.").max(128) });
export const registerSchema = z.object({
  username: z.string().min(3, "Use at least 3 characters.").max(32).regex(/^[a-z][a-z0-9_]*$/, "Start with a lowercase letter; use letters, numbers, or underscores."),
  email,
  password: z.string().min(12, "Use at least 12 characters.").max(128, "Use no more than 128 characters.").refine(value => [/([a-z])/, /([A-Z])/, /([0-9])/, /([^a-zA-Z0-9])/].filter(pattern => pattern.test(value)).length >= 3, "Use at least 3 types: lowercase, uppercase, numbers, symbols."),
  confirmPassword: z.string().min(1, "Confirm your password."),
}).refine(value => value.password === value.confirmPassword, { message: "Passwords do not match.", path: ["confirmPassword"] });
export type LoginValues = z.input<typeof loginSchema>;
export type RegisterValues = z.input<typeof registerSchema>;
