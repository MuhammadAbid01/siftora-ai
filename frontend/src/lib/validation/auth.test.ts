import { describe, expect, it } from "vitest";
import { signUpSchema, updatePasswordSchema } from "./auth";

describe("signUpSchema", () => {
  it("accepts a valid email and password", () => {
    const result = signUpSchema.safeParse({ email: "user@example.com", password: "longenough" });
    expect(result.success).toBe(true);
  });

  it("rejects an invalid email", () => {
    const result = signUpSchema.safeParse({ email: "not-an-email", password: "longenough" });
    expect(result.success).toBe(false);
  });

  it("rejects a short password", () => {
    const result = signUpSchema.safeParse({ email: "user@example.com", password: "short" });
    expect(result.success).toBe(false);
  });
});

describe("updatePasswordSchema", () => {
  it("rejects mismatched passwords", () => {
    const result = updatePasswordSchema.safeParse({
      password: "longenough1",
      confirmPassword: "longenough2",
    });
    expect(result.success).toBe(false);
  });

  it("accepts matching passwords", () => {
    const result = updatePasswordSchema.safeParse({
      password: "longenough1",
      confirmPassword: "longenough1",
    });
    expect(result.success).toBe(true);
  });
});
