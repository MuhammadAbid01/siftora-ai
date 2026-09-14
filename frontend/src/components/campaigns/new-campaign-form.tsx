"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { newCampaignSchema, type NewCampaignValues } from "@/lib/validation/campaigns";
import { apiPost, ApiError } from "@/lib/api-client";
import { campaignResponseSchema } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

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
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div className="space-y-1.5">
        <Label htmlFor="brief">Campaign brief</Label>
        <textarea
          id="brief"
          rows={4}
          placeholder="Find animation and design agencies in Dubai with 5-50 employees, an active website, and signs they could benefit from AI customer support."
          className="flex w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          {...register("brief")}
        />
        {errors.brief && (
          <p role="alert" className="text-sm text-red-600">
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
          <p role="alert" className="text-sm text-red-600">
            {errors.target_lead_count.message}
          </p>
        )}
      </div>
      {serverError && (
        <p role="alert" className="text-sm text-red-600">
          {serverError}
        </p>
      )}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? "Creating..." : "Create campaign"}
      </Button>
    </form>
  );
}
