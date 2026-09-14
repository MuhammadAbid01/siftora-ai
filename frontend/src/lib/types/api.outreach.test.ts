import { describe, expect, it } from "vitest";
import {
  approvalResponseSchema,
  leadDetailWithApprovalsResponseSchema,
  outreachDraftResponseSchema,
} from "./api";

const draft = {
  id: "draft-1",
  lead_id: "lead-1",
  channel: "email" as const,
  subject: "Quick question for Acme",
  body: "Hi Acme team,\n\nWe noticed...\n\nBest regards",
  version: 1,
  quality_status: "passed" as const,
  evidence_refs: [0],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("outreachDraftResponseSchema", () => {
  it("parses a passing draft", () => {
    expect(outreachDraftResponseSchema.safeParse(draft).success).toBe(true);
  });

  it("parses a needs_review draft with no evidence refs", () => {
    const result = outreachDraftResponseSchema.safeParse({
      ...draft,
      quality_status: "needs_review",
      evidence_refs: [],
    });
    expect(result.success).toBe(true);
  });

  it("rejects an unknown channel", () => {
    const result = outreachDraftResponseSchema.safeParse({ ...draft, channel: "sms" });
    expect(result.success).toBe(false);
  });
});

describe("approvalResponseSchema", () => {
  it("parses a pending approval", () => {
    const result = approvalResponseSchema.safeParse({
      id: "approval-1",
      draft,
      lead_id: "lead-1",
      campaign_id: "campaign-1",
      company: { id: "company-1", domain: "acme.example", name: "Acme" },
      lead_status: "qualified",
      lead_score: 92,
      status: "pending",
      reviewer_id: null,
      decided_at: null,
      edited: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    expect(result.success).toBe(true);
  });

  it("parses an approved approval with reviewer and timestamp", () => {
    const result = approvalResponseSchema.safeParse({
      id: "approval-1",
      draft,
      lead_id: "lead-1",
      campaign_id: "campaign-1",
      company: { id: "company-1", domain: "acme.example", name: "Acme" },
      lead_status: "qualified",
      lead_score: 92,
      status: "approved",
      reviewer_id: "user-1",
      decided_at: "2026-01-02T00:00:00Z",
      edited: false,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-02T00:00:00Z",
    });
    expect(result.success).toBe(true);
  });
});

describe("leadDetailWithApprovalsResponseSchema", () => {
  it("parses a lead with an approvals array", () => {
    const result = leadDetailWithApprovalsResponseSchema.safeParse({
      id: "lead-1",
      campaign_id: "campaign-1",
      company: { id: "company-1", domain: "acme.example", name: "Acme" },
      source_url: "https://acme.example",
      status: "qualified",
      score: 92,
      decision_reason: null,
      evidence: [],
      score_breakdown: [],
      approvals: [
        {
          id: "approval-1",
          draft,
          lead_id: "lead-1",
          campaign_id: "campaign-1",
          company: { id: "company-1", domain: "acme.example", name: "Acme" },
          lead_status: "qualified",
          lead_score: 92,
          status: "pending",
          reviewer_id: null,
          decided_at: null,
          edited: false,
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    expect(result.success).toBe(true);
  });
});
