import { z } from "zod";

export const newCampaignSchema = z.object({
  brief: z
    .string()
    .trim()
    .min(10, "Describe your campaign in at least 10 characters")
    .max(2000, "Brief must be under 2000 characters"),
  offer: z.string().trim().max(500).optional().or(z.literal("")),
  target_lead_count: z.coerce.number().int().min(1).max(200),
});
export type NewCampaignValues = z.infer<typeof newCampaignSchema>;

// Comma-separated free text in the UI, parsed into a string array on submit.
const listField = z.string().transform((value) =>
  value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean),
);

// Blank string inputs are treated as "not provided" rather than coerced to 0.
const optionalCompanySize = z.preprocess(
  (value) => (value === "" || value === undefined ? undefined : value),
  z.coerce.number().int().min(0).optional(),
);

export const icpFormSchema = z
  .object({
    industries: listField,
    locations: listField,
    company_size_min: optionalCompanySize,
    company_size_max: optionalCompanySize,
    signals: listField,
    exclusions: listField,
    target_roles: listField,
  })
  .refine(
    (data) =>
      data.company_size_min === undefined ||
      data.company_size_max === undefined ||
      data.company_size_min <= data.company_size_max,
    {
      message: "Minimum company size must be less than or equal to the maximum",
      path: ["company_size_max"],
    },
  );
export type IcpFormInput = z.input<typeof icpFormSchema>;
export type IcpFormValues = z.infer<typeof icpFormSchema>;

export const scoreWeightsFormSchema = z
  .object({
    industry_fit: z.coerce.number().int().min(0).max(100),
    geography_fit: z.coerce.number().int().min(0).max(100),
    company_size_fit: z.coerce.number().int().min(0).max(100),
    pain_point_evidence: z.coerce.number().int().min(0).max(100),
    buying_signal: z.coerce.number().int().min(0).max(100),
    contact_relevance: z.coerce.number().int().min(0).max(100),
    recency: z.coerce.number().int().min(0).max(100),
    evidence_completeness: z.coerce.number().int().min(0).max(100),
  })
  .refine((weights) => Object.values(weights).reduce((sum, value) => sum + value, 0) === 100, {
    message: "Weights must sum to exactly 100",
    path: ["industry_fit"],
  });
export type ScoreWeightsFormValues = z.infer<typeof scoreWeightsFormSchema>;

export const scoreThresholdsFormSchema = z
  .object({
    qualified_min: z.coerce.number().int().min(0).max(100),
    needs_review_min: z.coerce.number().int().min(0).max(100),
  })
  .refine((data) => data.needs_review_min < data.qualified_min, {
    message: "Needs-review threshold must be lower than the qualified threshold",
    path: ["needs_review_min"],
  });
export type ScoreThresholdsFormValues = z.infer<typeof scoreThresholdsFormSchema>;

export const runLimitsFormSchema = z.object({
  max_queries: z.coerce.number().int().min(1).max(100),
  max_pages_per_company: z.coerce.number().int().min(1).max(20),
  max_retries: z.coerce.number().int().min(0).max(5),
  max_cost_usd: z.coerce.number().min(0.01).max(50),
});
export type RunLimitsFormValues = z.infer<typeof runLimitsFormSchema>;

export const senderFormSchema = z.object({
  sender_name: z.string().trim().max(200).optional().or(z.literal("")),
  sender_email: z.string().trim().email("Enter a valid email").optional().or(z.literal("")),
});
export type SenderFormValues = z.infer<typeof senderFormSchema>;
