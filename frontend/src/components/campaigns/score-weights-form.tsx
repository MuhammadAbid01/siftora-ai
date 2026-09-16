"use client";

import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { scoreWeightsFormSchema, type ScoreWeightsFormValues } from "@/lib/validation/campaigns";
import { apiPatch, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse, type ScoreWeights } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";

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
          <div className="flex items-center gap-3">
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
              <div
                className={cn(
                  "h-full rounded-full transition-[width] duration-300 ease-out motion-reduce:transition-none",
                  total === 100 ? "bg-emerald-500" : "bg-amber-500",
                )}
                style={{ width: `${Math.min(total, 100)}%` }}
              />
            </div>
            <p
              role="status"
              className={cn(
                "shrink-0 text-sm font-medium tabular-nums",
                total === 100
                  ? "text-slate-600 dark:text-slate-400"
                  : "text-amber-700 dark:text-amber-400",
              )}
            >
              {total} / 100
            </p>
          </div>
          {errors.industry_fit && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {errors.industry_fit.message}
            </p>
          )}
          {serverError && <Alert>{serverError}</Alert>}
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
