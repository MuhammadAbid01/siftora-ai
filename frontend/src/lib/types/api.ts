import { z } from "zod";

// Mirrors backend/app/schemas.py — keep these in sync manually (see
// specs/phase-1-foundation.md, "Frontend" design notes).

export const healthResponseSchema = z.object({
  status: z.literal("ok"),
  version: z.string(),
});
export type HealthResponse = z.infer<typeof healthResponseSchema>;

export const profileResponseSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  role: z.enum(["user", "admin"]),
  created_at: z.string(),
  updated_at: z.string(),
});
export type ProfileResponse = z.infer<typeof profileResponseSchema>;

export const apiErrorResponseSchema = z.object({
  error: z.object({
    code: z.string(),
    message: z.string(),
    details: z.record(z.string(), z.unknown()).optional(),
  }),
});
export type ApiErrorResponse = z.infer<typeof apiErrorResponseSchema>;

// --- Campaigns (Phase 2) ------------------------------------------------
// Mirrors backend/app/schemas.py campaign models — see
// specs/phase-2-campaigns.md, "Frontend additions".

export const campaignStatusSchema = z.enum([
  "draft",
  "awaiting_plan_approval",
  "plan_approved",
  "queued",
  "running",
  "completed",
  "failed",
  "paused",
]);
export type CampaignStatus = z.infer<typeof campaignStatusSchema>;

export const scoreWeightsSchema = z.object({
  industry_fit: z.number().int(),
  geography_fit: z.number().int(),
  company_size_fit: z.number().int(),
  pain_point_evidence: z.number().int(),
  buying_signal: z.number().int(),
  contact_relevance: z.number().int(),
  recency: z.number().int(),
  evidence_completeness: z.number().int(),
});
export type ScoreWeights = z.infer<typeof scoreWeightsSchema>;

export const scoreThresholdsSchema = z.object({
  qualified_min: z.number().int(),
  needs_review_min: z.number().int(),
});
export type ScoreThresholds = z.infer<typeof scoreThresholdsSchema>;

export const runLimitsSchema = z.object({
  max_queries: z.number().int(),
  max_pages_per_company: z.number().int(),
  max_retries: z.number().int(),
  max_cost_usd: z.number(),
});
export type RunLimits = z.infer<typeof runLimitsSchema>;

export const icpSchema = z.object({
  industries: z.array(z.string()),
  locations: z.array(z.string()),
  company_size_min: z.number().int().nullable(),
  company_size_max: z.number().int().nullable(),
  signals: z.array(z.string()),
  exclusions: z.array(z.string()),
  target_roles: z.array(z.string()),
});
export type ICP = z.infer<typeof icpSchema>;

export const searchPlanQuerySchema = z.object({
  query: z.string(),
  rationale: z.string(),
});
export type SearchPlanQueryItem = z.infer<typeof searchPlanQuerySchema>;

export const campaignResponseSchema = z.object({
  id: z.string(),
  status: campaignStatusSchema,
  brief: z.string(),
  offer: z.string().nullable(),
  target_lead_count: z.number().int(),
  icp: icpSchema.nullable(),
  search_plan: z.array(searchPlanQuerySchema).nullable(),
  score_weights: scoreWeightsSchema,
  score_thresholds: scoreThresholdsSchema,
  limits: runLimitsSchema,
  plan_approved_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type CampaignResponse = z.infer<typeof campaignResponseSchema>;

export const campaignListResponseSchema = z.object({
  items: z.array(campaignResponseSchema),
  next_cursor: z.string().nullable().optional(),
});
export type CampaignListResponse = z.infer<typeof campaignListResponseSchema>;

export const deleteResponseSchema = z.object({
  deleted: z.literal(true),
});
export type DeleteResponse = z.infer<typeof deleteResponseSchema>;

// --- Research (Phase 3) --------------------------------------------------
// Mirrors backend/app/schemas.py research models — see
// specs/phase-3-research.md, "Frontend" section.

export const criterionSchema = z.enum([
  "industry_fit",
  "geography_fit",
  "company_size_fit",
  "pain_point_evidence",
  "buying_signal",
  "contact_relevance",
  "recency",
  "evidence_completeness",
]);
export type Criterion = z.infer<typeof criterionSchema>;

export const leadStatusSchema = z.enum(["qualified", "needs_review", "rejected"]);
export type LeadStatus = z.infer<typeof leadStatusSchema>;

export const runStatusSchema = z.enum(["queued", "running", "completed", "failed", "paused"]);
export type RunStatus = z.infer<typeof runStatusSchema>;

export const evidenceItemSchema = z.object({
  type: z.enum(["fact", "inference", "unknown"]),
  claim: z.string(),
  excerpt: z.string().nullable().optional(),
  source_url: z.string().nullable().optional(),
  confidence: z.number().nullable().optional(),
});
export type EvidenceItem = z.infer<typeof evidenceItemSchema>;

export const companySummarySchema = z.object({
  id: z.string(),
  domain: z.string(),
  name: z.string(),
});
export type CompanySummary = z.infer<typeof companySummarySchema>;

export const scoreBreakdownItemSchema = z.object({
  criterion: criterionSchema,
  rating: z.number(),
  weight: z.number().int(),
  points: z.number(),
});
export type ScoreBreakdownItem = z.infer<typeof scoreBreakdownItemSchema>;

export const leadSummaryResponseSchema = z.object({
  id: z.string(),
  campaign_id: z.string(),
  company: companySummarySchema,
  source_url: z.string(),
  status: leadStatusSchema,
  score: z.number().int(),
  decision_reason: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type LeadSummaryResponse = z.infer<typeof leadSummaryResponseSchema>;

export const leadListResponseSchema = z.object({
  items: z.array(leadSummaryResponseSchema),
  next_cursor: z.string().nullable().optional(),
});
export type LeadListResponse = z.infer<typeof leadListResponseSchema>;

export const leadDetailResponseSchema = z.object({
  id: z.string(),
  campaign_id: z.string(),
  company: companySummarySchema,
  source_url: z.string(),
  status: leadStatusSchema,
  score: z.number().int(),
  decision_reason: z.string().nullable(),
  evidence: z.array(evidenceItemSchema),
  score_breakdown: z.array(scoreBreakdownItemSchema),
  created_at: z.string(),
  updated_at: z.string(),
});
export type LeadDetailResponse = z.infer<typeof leadDetailResponseSchema>;

export const campaignRunResponseSchema = z.object({
  id: z.string(),
  campaign_id: z.string(),
  status: runStatusSchema,
  stop_reason: z.string().nullable(),
  queries_used: z.number().int(),
  leads_created: z.number().int(),
  qualified_count: z.number().int(),
  needs_review_count: z.number().int(),
  rejected_count: z.number().int(),
  failed_count: z.number().int(),
  estimated_cost_usd: z.number(),
  error: z.string().nullable(),
  started_at: z.string(),
  completed_at: z.string().nullable(),
});
export type CampaignRunResponse = z.infer<typeof campaignRunResponseSchema>;

export const agentEventResponseSchema = z.object({
  id: z.string(),
  run_id: z.string(),
  node: z.string(),
  status: z.enum(["ok", "error"]),
  summary: z.string(),
  duration_ms: z.number().int().nullable(),
  error: z.string().nullable(),
  created_at: z.string(),
});
export type AgentEventResponse = z.infer<typeof agentEventResponseSchema>;

export const agentEventListResponseSchema = z.object({
  items: z.array(agentEventResponseSchema),
  next_cursor: z.string().nullable().optional(),
});
export type AgentEventListResponse = z.infer<typeof agentEventListResponseSchema>;

export const toolCallResponseSchema = z.object({
  id: z.string(),
  run_id: z.string(),
  tool: z.string(),
  provider: z.string(),
  status: z.enum(["ok", "error"]),
  summary: z.string(),
  latency_ms: z.number().int().nullable(),
  cost_usd: z.number().nullable(),
  created_at: z.string(),
});
export type ToolCallResponse = z.infer<typeof toolCallResponseSchema>;

export const toolCallListResponseSchema = z.object({
  items: z.array(toolCallResponseSchema),
  next_cursor: z.string().nullable().optional(),
});
export type ToolCallListResponse = z.infer<typeof toolCallListResponseSchema>;
