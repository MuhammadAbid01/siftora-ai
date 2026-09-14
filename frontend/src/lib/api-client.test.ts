import { describe, expect, it, vi, afterEach } from "vitest";
import { z } from "zod";
import { apiGet, ApiError } from "./api-client";

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      json: async () => body,
    }),
  );
}

const schema = z.object({ status: z.literal("ok") });

describe("apiGet", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed data on a successful response", async () => {
    mockFetchOnce(200, { status: "ok" });

    const result = await apiGet("/api/health", schema);

    expect(result).toEqual({ status: "ok" });
  });

  it("throws an ApiError with the server error code on a non-2xx response", async () => {
    mockFetchOnce(401, { error: { code: "unauthorized", message: "Not signed in" } });

    await expect(apiGet("/api/me", schema)).rejects.toMatchObject({
      status: 401,
      code: "unauthorized",
    });
  });

  it("throws an ApiError when the response does not match the expected shape", async () => {
    mockFetchOnce(200, { unexpected: true });

    const error = await apiGet("/api/health", schema).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("invalid_response_shape");
  });

  it("throws a network_error ApiError when fetch rejects", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("network down")));

    const error = await apiGet("/api/health", schema).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("network_error");
  });
});
