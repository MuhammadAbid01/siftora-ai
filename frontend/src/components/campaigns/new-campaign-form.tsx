"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { newCampaignSchema, type NewCampaignValues } from "@/lib/validation/campaigns";
import { apiPost, ApiError } from "@/lib/api-client";
import { campaignResponseSchema } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export function NewCampaignForm() {
  const router = useRouter();
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<NewCampaignValues>({
    resolver: zodResolver(newCampaignSchema),
    defaultValues: { target_lead_count: 20 },
  });

  const onSubmit = async (values: NewCampaignValues) => {
    setServerError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setServerError("Your session has expired. Please sign in again.");
      return;
    }

    try {
      const campaign = await apiPost(
        "/api/campaigns",
        {
          brief: values.brief,
          offer: values.offer || undefined,
          target_lead_count: values.target_lead_count,
        },
        campaignResponseSchema,
        { accessToken },
      );
      router.push(`/dashboard/campaigns/${campaign.id}`);
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : "Could not create the campaign.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Campaign brief</CardTitle>
        <CardDescription>
          Describe who you&apos;re trying to reach in plain language.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
          <div className="space-y-1.5">
            <Label htmlFor="brief">Brief</Label>
            <Textarea
              id="brief"
              rows={5}
              placeholder="Find animation and design agencies in Dubai with 5-50 employees, an active website, and signs they could benefit from AI customer support."
              {...register("brief")}
            />
            {errors.brief && (
              <p role="alert" className="text-sm text-red-600 dark:text-red-400">
                {errors.brief.message}
              </p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="offer">Offer (optional)</Label>
            <Input id="offer" placeholder="AI customer support automation" {...register("offer")} />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="target_lead_count">Target lead count</Label>
            <Input
              id="target_lead_count"
              type="number"
              min={1}
              max={200}
              {...register("target_lead_count")}
            />
            {errors.target_lead_count && (
              <p role="alert" className="text-sm text-red-600 dark:text-red-400">
                {errors.target_lead_count.message}
              </p>
            )}
          </div>
          {serverError && <Alert>{serverError}</Alert>}
          <div className="flex items-center justify-end gap-3 border-t border-slate-100 pt-5 dark:border-slate-800">
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Creating..." : "Create campaign"}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
