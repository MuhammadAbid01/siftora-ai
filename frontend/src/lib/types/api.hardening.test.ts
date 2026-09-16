import { describe, expect, it } from "vitest";
import {
  campaignAnalyticsResponseSchema,
  demoResetResponseSchema,
  evalReportSchema,
  readinessResponseSchema,
} from "./api";

describe("readinessResponseSchema", () => {
  it("parses a healthy readiness response", () => {
    const result = readinessResponseSchema.safeParse({ status: "ok", database: "ok" });
    expect(result.success).toBe(true);
  });

  it("parses an unreachable-database response", () => {
    const result = readinessResponseSchema.safeParse({
      status: "error",
      database: "unreachable",
    });
    expect(result.success).toBe(true);
  });
});

describe("evalReportSchema", () => {
  it("parses a full report across all six categories", () => {
    const category = {
      category: "scoring",
      total: 20,
      passed: 20,
      pass_rate: 1.0,
      cases: [{ name: "all_ones", passed: true, detail: null }],
    };
    const result = evalReportSchema.safeParse({
      categories: [category],
      overall_pass_rate: 1.0,
      provider_mode: { llm: "fixture", search: "fixture", extraction: "fixture" },
    });
    expect(result.success).toBe(true);
  });

  it("parses a case with a failure detail", () => {
    const result = evalReportSchema.safeParse({
      categories: [
        {
          category: "deduplication",
          total: 15,
          passed: 14,
          pass_rate: 14 / 15,
          cases: [{ name: "bad_case", passed: false, detail: "got 'wrong.example'" }],
        },
      ],
      overall_pass_rate: 14 / 15,
      provider_mode: { llm: "fixture", search: "fixture", extraction: "fixture" },
    });
    expect(result.success).toBe(true);
  });
});

describe("campaignAnalyticsResponseSchema", () => {
  it("parses a full analytics response", () => {
    const result = campaignAnalyticsResponseSchema.safeParse({
      campaign_id: "campaign-1",
      qualified_count: 2,
      needs_review_count: 1,
      rejected_count: 3,
      drafts_generated: 2,
      drafts_approved: 1,
      drafts_rejected: 0,
      total_cost_usd: 0.15,
      total_queries_used: 4,
      avg_tool_latency_ms: 120.5,
      tool_call_failures: 1,
      agent_event_failures: 0,
      runs_count: 1,
    });
    expect(result.success).toBe(true);
  });

  it("allows a null avg_tool_latency_ms when no tool call recorded latency", () => {
    const result = campaignAnalyticsResponseSchema.safeParse({
      campaign_id: "campaign-1",
      qualified_count: 0,
      needs_review_count: 0,
      rejected_count: 0,
      drafts_generated: 0,
      drafts_approved: 0,
      drafts_rejected: 0,
      total_cost_usd: 0,
      total_queries_used: 0,
      avg_tool_latency_ms: null,
      tool_call_failures: 0,
      agent_event_failures: 0,
      runs_count: 1,
    });
    expect(result.success).toBe(true);
  });
});

describe("demoResetResponseSchema", () => {
  it("parses a reset count", () => {
    const result = demoResetResponseSchema.safeParse({ deleted_campaigns: 3 });
    expect(result.success).toBe(true);
  });
});
