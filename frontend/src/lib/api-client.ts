import type { z } from "zod";
import { env } from "@/lib/env";
import { apiErrorResponseSchema } from "@/lib/types/api";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown> | undefined;

  constructor(status: number, code: string, message: string, details?: Record<string, unknown>) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

type RequestOptions = {
  accessToken?: string | null;
  signal?: AbortSignal;
};

async function request<Schema extends z.ZodTypeAny>(
  method: "GET" | "POST" | "PATCH" | "DELETE",
  path: string,
  schema: Schema,
  body?: unknown,
  options?: RequestOptions,
): Promise<z.infer<Schema>> {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }
  if (options?.accessToken) {
    headers.Authorization = `Bearer ${options.accessToken}`;
  }

  let response: Response;
  try {
    response = await fetch(`${env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
      method,
      headers,
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: options?.signal,
    });
  } catch {
    throw new ApiError(0, "network_error", "Unable to reach the Siftora API.");
  }

  const rawBody: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const parsedError = apiErrorResponseSchema.safeParse(rawBody);
    if (parsedError.success) {
      throw new ApiError(
        response.status,
        parsedError.data.error.code,
        parsedError.data.error.message,
        // The wire format uses `null` for "no extra detail"; ApiError
        // exposes it as `undefined` so callers can use plain optional
        // chaining (`err.details?.missing_fields`).
        parsedError.data.error.details ?? undefined,
      );
    }
    throw new ApiError(response.status, "unknown_error", "An unexpected error occurred.");
  }

  const parsed = schema.safeParse(rawBody);
  if (!parsed.success) {
    throw new ApiError(
      response.status,
      "invalid_response_shape",
      "The API response did not match the expected shape.",
    );
  }

  return parsed.data;
}

export function apiGet<Schema extends z.ZodTypeAny>(
  path: string,
  schema: Schema,
  options?: RequestOptions,
): Promise<z.infer<Schema>> {
  return request("GET", path, schema, undefined, options);
}

export function apiPost<Schema extends z.ZodTypeAny>(
  path: string,
  body: unknown,
  schema: Schema,
  options?: RequestOptions,
): Promise<z.infer<Schema>> {
  return request("POST", path, schema, body, options);
}

export function apiPatch<Schema extends z.ZodTypeAny>(
  path: string,
  body: unknown,
  schema: Schema,
  options?: RequestOptions,
): Promise<z.infer<Schema>> {
  return request("PATCH", path, schema, body, options);
}

export function apiDelete<Schema extends z.ZodTypeAny>(
  path: string,
  schema: Schema,
  options?: RequestOptions,
): Promise<z.infer<Schema>> {
  return request("DELETE", path, schema, undefined, options);
}
