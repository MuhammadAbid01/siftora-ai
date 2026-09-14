"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  scoreThresholdsFormSchema,
  type ScoreThresholdsFormValues,
} from "@/lib/validation/campaigns";
import { apiPatch, ApiError } from "@/lib/api-client";
import {
  campaignResponseSchema,
  type CampaignResponse,
  type ScoreThresholds,
} from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ScoreThresholdsForm({
  campaignId,
  thresholds,
  onSaved,
}: {
  campaignId: string;
  thresholds: ScoreThresholds;
  onSaved: (campaign: CampaignResponse) => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<ScoreThresholdsFormValues>({
    resolver: zodResolver(scoreThresholdsFormSchema),
    defaultValues: thresholds,
  });

  const onSubmit = async (values: ScoreThresholdsFormValues) => {
    setServerError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setServerError("Your session has expired. Please sign in again.");
      return;
    }

    try {
      const campaign = await apiPatch(
        `/api/campaigns/${campaignId}`,
        { score_thresholds: values },
        campaignResponseSchema,
        { accessToken },
      );
      onSaved(campaign);
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : "Could not save the thresholds.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Score thresholds</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="qualified_min">Qualified (score ≥)</Label>
              <Input
                id="qualified_min"
                type="number"
                min={0}
                max={100}
                {...register("qualified_min")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="needs_review_min">Needs review (score ≥)</Label>
              <Input
                id="needs_review_min"
                type="number"
                min={0}
                max={100}
                {...register("needs_review_min")}
              />
            </div>
          </div>
          {errors.needs_review_min && (
            <p role="alert" className="text-sm text-red-600">
              {errors.needs_review_min.message}
            </p>
          )}
          {serverError && (
            <p role="alert" className="text-sm text-red-600">
              {serverError}
            </p>
          )}
          <Button type="submit" variant="secondary" size="sm" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save thresholds"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
