import { describe, expect, it } from "vitest";
import {
  icpFormSchema,
  newCampaignSchema,
  runLimitsFormSchema,
  scoreThresholdsFormSchema,
  scoreWeightsFormSchema,
} from "./campaigns";

describe("newCampaignSchema", () => {
  it("accepts a valid brief and default target count", () => {
    const result = newCampaignSchema.safeParse({
      brief: "Find design agencies in Dubai with 5-50 employees.",
      target_lead_count: 20,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a brief shorter than 10 characters", () => {
    const result = newCampaignSchema.safeParse({ brief: "too short", target_lead_count: 20 });
    expect(result.success).toBe(false);
  });

  it("rejects a target lead count above 200", () => {
    const result = newCampaignSchema.safeParse({
      brief: "Find design agencies in Dubai with 5-50 employees.",
      target_lead_count: 500,
    });
    expect(result.success).toBe(false);
  });
});

describe("icpFormSchema", () => {
  it("splits comma-separated fields into trimmed arrays", () => {
    const result = icpFormSchema.parse({
      industries: "Design agencies,  Animation studios ",
      locations: "Dubai;London",
      signals: "",
      exclusions: "",
      target_roles: "Owner, Marketing Manager",
    });

    expect(result.industries).toEqual(["Design agencies", "Animation studios"]);
    expect(result.locations).toEqual(["Dubai;London"]);
    expect(result.signals).toEqual([]);
  });

  it("treats blank company size inputs as unset rather than 0", () => {
    const result = icpFormSchema.parse({
      industries: "",
      locations: "",
      signals: "",
      exclusions: "",
      target_roles: "",
      company_size_min: "",
      company_size_max: "",
    });

    expect(result.company_size_min).toBeUndefined();
    expect(result.company_size_max).toBeUndefined();
  });

  it("rejects a minimum company size greater than the maximum", () => {
    const result = icpFormSchema.safeParse({
      industries: "",
      locations: "",
      signals: "",
      exclusions: "",
      target_roles: "",
      company_size_min: "100",
      company_size_max: "10",
    });

    expect(result.success).toBe(false);
  });
});

describe("scoreWeightsFormSchema", () => {
  const baseWeights = {
    industry_fit: 20,
    geography_fit: 10,
    company_size_fit: 10,
    pain_point_evidence: 20,
    buying_signal: 15,
    contact_relevance: 10,
    recency: 10,
    evidence_completeness: 5,
  };

  it("accepts weights that sum to exactly 100", () => {
    expect(scoreWeightsFormSchema.safeParse(baseWeights).success).toBe(true);
  });

  it("rejects weights that do not sum to 100", () => {
    const result = scoreWeightsFormSchema.safeParse({ ...baseWeights, industry_fit: 50 });
    expect(result.success).toBe(false);
  });
});

describe("scoreThresholdsFormSchema", () => {
  it("accepts a properly ordered pair", () => {
    const result = scoreThresholdsFormSchema.safeParse({ qualified_min: 75, needs_review_min: 55 });
    expect(result.success).toBe(true);
  });

  it("rejects needs_review_min at or above qualified_min", () => {
    const result = scoreThresholdsFormSchema.safeParse({ qualified_min: 60, needs_review_min: 60 });
    expect(result.success).toBe(false);
  });
});

describe("runLimitsFormSchema", () => {
  it("accepts defaults", () => {
    const result = runLimitsFormSchema.safeParse({
      max_queries: 20,
      max_pages_per_company: 5,
      max_retries: 2,
      max_cost_usd: 5,
    });
    expect(result.success).toBe(true);
  });

  it("rejects a cost limit above 50", () => {
    const result = runLimitsFormSchema.safeParse({
      max_queries: 20,
      max_pages_per_company: 5,
      max_retries: 2,
      max_cost_usd: 51,
    });
    expect(result.success).toBe(false);
  });
});
