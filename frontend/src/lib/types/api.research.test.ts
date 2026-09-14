import { describe, expect, it } from "vitest";
import {
  agentEventResponseSchema,
  campaignRunResponseSchema,
  evidenceItemSchema,
  leadDetailResponseSchema,
} from "./api";

describe("evidenceItemSchema", () => {
  it("accepts a fact with excerpt and source", () => {
    const result = evidenceItemSchema.safeParse({
      type: "fact",
      claim: "Northbeam has 22 employees.",
      excerpt: "...22 employees.",
      source_url: "https://northbeamstudio.example",
      confidence: 0.9,
    });
    expect(result.success).toBe(true);
  });

  it("accepts an unknown with no excerpt or source", () => {
    const result = evidenceItemSchema.safeParse({
      type: "unknown",
      claim: "No pricing found.",
    });
    expect(result.success).toBe(true);
  });
});

describe("campaignRunResponseSchema", () => {
  it("parses a completed run", () => {
    const result = campaignRunResponseSchema.safeParse({
      id: "run-1",
      campaign_id: "campaign-1",
      status: "completed",
      stop_reason: "target_reached",
      queries_used: 3,
      leads_created: 5,
      qualified_count: 2,
      needs_review_count: 1,
      rejected_count: 2,
      failed_count: 0,
      estimated_cost_usd: 0.15,
      error: null,
      started_at: "2026-01-01T00:00:00Z",
      completed_at: "2026-01-01T00:01:00Z",
    });
    expect(result.success).toBe(true);
  });
});

describe("leadDetailResponseSchema", () => {
  it("parses a lead with evidence and a score breakdown", () => {
    const result = leadDetailResponseSchema.safeParse({
      id: "lead-1",
      campaign_id: "campaign-1",
      company: { id: "company-1", domain: "example.com", name: "Example Co" },
      source_url: "https://example.com",
      status: "qualified",
      score: 92,
      decision_reason: null,
      evidence: [
        {
          type: "fact",
          claim: "x",
          excerpt: "y",
          source_url: "https://example.com",
          confidence: 0.9,
        },
      ],
      score_breakdown: [{ criterion: "industry_fit", rating: 1, weight: 20, points: 20 }],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    expect(result.success).toBe(true);
  });
});

describe("agentEventResponseSchema", () => {
  it("parses an ok event", () => {
    const result = agentEventResponseSchema.safeParse({
      id: "event-1",
      run_id: "run-1",
      node: "complete_run",
      status: "ok",
      summary: "Run finished: target_reached.",
      duration_ms: null,
      error: null,
      created_at: "2026-01-01T00:00:00Z",
    });
    expect(result.success).toBe(true);
  });
});
