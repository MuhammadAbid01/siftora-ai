"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { runLimitsFormSchema, type RunLimitsFormValues } from "@/lib/validation/campaigns";
import { apiPatch, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse, type RunLimits } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function RunLimitsForm({
  campaignId,
  limits,
  onSaved,
}: {
  campaignId: string;
  limits: RunLimits;
  onSaved: (campaign: CampaignResponse) => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<RunLimitsFormValues>({
    resolver: zodResolver(runLimitsFormSchema),
    defaultValues: limits,
  });

  const onSubmit = async (values: RunLimitsFormValues) => {
    setServerError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setServerError("Your session has expired. Please sign in again.");
      return;
    }

    try {
      const campaign = await apiPatch(
        `/api/campaigns/${campaignId}`,
        { limits: values },
        campaignResponseSchema,
        { accessToken },
      );
      onSaved(campaign);
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : "Could not save the run limits.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Run limits</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="max_queries">Max search queries</Label>
              <Input
                id="max_queries"
                type="number"
                min={1}
                max={100}
                {...register("max_queries")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="max_pages_per_company">Max pages per company</Label>
              <Input
                id="max_pages_per_company"
                type="number"
                min={1}
                max={20}
                {...register("max_pages_per_company")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="max_retries">Max retries</Label>
              <Input id="max_retries" type="number" min={0} max={5} {...register("max_retries")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="max_cost_usd">Max cost (USD)</Label>
              <Input
                id="max_cost_usd"
                type="number"
                min={0.01}
                max={50}
                step="0.01"
                {...register("max_cost_usd")}
              />
            </div>
          </div>
          {serverError && (
            <p role="alert" className="text-sm text-red-600">
              {serverError}
            </p>
          )}
          <Button type="submit" variant="secondary" size="sm" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save limits"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
