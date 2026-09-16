"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { senderFormSchema, type SenderFormValues } from "@/lib/validation/campaigns";
import { apiPatch, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SenderForm({
  campaignId,
  senderName,
  senderEmail,
  onSaved,
}: {
  campaignId: string;
  senderName: string | null | undefined;
  senderEmail: string | null | undefined;
  onSaved: (campaign: CampaignResponse) => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<SenderFormValues>({
    resolver: zodResolver(senderFormSchema),
    defaultValues: { sender_name: senderName ?? "", sender_email: senderEmail ?? "" },
  });

  const onSubmit = async (values: SenderFormValues) => {
    setServerError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setServerError("Your session has expired. Please sign in again.");
      return;
    }

    try {
      const campaign = await apiPatch(
        `/api/campaigns/${campaignId}`,
        {
          sender_name: values.sender_name || undefined,
          sender_email: values.sender_email || undefined,
        },
        campaignResponseSchema,
        { accessToken },
      );
      onSaved(campaign);
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : "Could not save sender details.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Sender details</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-sm text-slate-600 dark:text-slate-400">
          Used as the signoff on generated outreach drafts.
        </p>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="sender_name">Your name</Label>
              <Input id="sender_name" placeholder="Jamie Rivera" {...register("sender_name")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="sender_email">Your email</Label>
              <Input
                id="sender_email"
                type="email"
                placeholder="jamie@example.com"
                {...register("sender_email")}
              />
            </div>
          </div>
          {errors.sender_email && (
            <p role="alert" className="text-sm text-red-600 dark:text-red-400">
              {errors.sender_email.message}
            </p>
          )}
          {serverError && <Alert>{serverError}</Alert>}
          <Button type="submit" variant="secondary" size="sm" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save sender details"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
