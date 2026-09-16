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

  it("preserves the server error code when details is null", async () => {
    // The backend serializes ErrorDetail with model_dump(), so `details` is
    // always present and is `null` when the error carries no extra detail.
    // This used to fail schema parsing, which threw away the real code and
    // reported "An unexpected error occurred." instead — so callers could
    // never recognise e.g. `no_run_yet` and a campaign with no run yet
    // showed a spurious error on the page.
    mockFetchOnce(404, {
      error: { code: "no_run_yet", message: "This campaign has not been run yet.", details: null },
    });

    const error = await apiGet("/api/campaigns/abc/progress", schema).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).code).toBe("no_run_yet");
    expect((error as ApiError).message).toBe("This campaign has not been run yet.");
    expect((error as ApiError).details).toBeUndefined();
  });

  it("exposes details when the server provides them", async () => {
    mockFetchOnce(422, {
      error: {
        code: "icp_incomplete",
        message: "Not enough information.",
        details: { missing_fields: ["industries"] },
      },
    });

    const error = await apiGet("/api/campaigns/abc/plan", schema).catch((e: unknown) => e);

    expect((error as ApiError).code).toBe("icp_incomplete");
    expect((error as ApiError).details).toEqual({ missing_fields: ["industries"] });
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
