"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { scoreWeightsFormSchema, type ScoreWeightsFormValues } from "@/lib/validation/campaigns";
import { apiPatch, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse, type ScoreWeights } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const WEIGHT_FIELDS: { key: keyof ScoreWeightsFormValues; label: string }[] = [
  { key: "industry_fit", label: "Industry fit" },
  { key: "geography_fit", label: "Geography fit" },
  { key: "company_size_fit", label: "Company-size fit" },
  { key: "pain_point_evidence", label: "Pain-point evidence" },
  { key: "buying_signal", label: "Buying/tech signal" },
  { key: "contact_relevance", label: "Contact relevance" },
  { key: "recency", label: "Website/activity recency" },
  { key: "evidence_completeness", label: "Evidence completeness" },
];

export function ScoreWeightsForm({
  campaignId,
  weights,
  onSaved,
}: {
  campaignId: string;
  weights: ScoreWeights;
  onSaved: (campaign: CampaignResponse) => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<ScoreWeightsFormValues>({
    resolver: zodResolver(scoreWeightsFormSchema),
    defaultValues: weights,
  });

  const liveValues = useWatch({ control });
  const total = WEIGHT_FIELDS.reduce((sum, field) => sum + (Number(liveValues[field.key]) || 0), 0);

  const onSubmit = async (values: ScoreWeightsFormValues) => {
    setServerError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setServerError("Your session has expired. Please sign in again.");
      return;
    }

    try {
      const campaign = await apiPatch(
        `/api/campaigns/${campaignId}`,
        { score_weights: values },
        campaignResponseSchema,
        { accessToken },
      );
      onSaved(campaign);
    } catch (error) {
      setServerError(
        error instanceof ApiError ? error.message : "Could not save the scoring weights.",
      );
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Scoring weights</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            {WEIGHT_FIELDS.map((field) => (
              <div key={field.key} className="space-y-1.5">
                <Label htmlFor={field.key}>{field.label}</Label>
                <Input id={field.key} type="number" min={0} max={100} {...register(field.key)} />
              </div>
            ))}
          </div>
          <p
            role="status"
            className={
              total === 100 ? "text-sm text-slate-600" : "text-sm font-medium text-red-600"
            }
          >
            Total: {total} / 100
          </p>
          {errors.industry_fit && (
            <p role="alert" className="text-sm text-red-600">
              {errors.industry_fit.message}
            </p>
          )}
          {serverError && (
            <p role="alert" className="text-sm text-red-600">
              {serverError}
            </p>
          )}
          <Button
            type="submit"
            variant="secondary"
            size="sm"
            disabled={isSubmitting || total !== 100}
          >
            {isSubmitting ? "Saving..." : "Save weights"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
