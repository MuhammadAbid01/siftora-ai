"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { icpFormSchema, type IcpFormInput, type IcpFormValues } from "@/lib/validation/campaigns";
import { apiPatch, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse, type ICP } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function toDisplayList(values: string[]): string {
  return values.join(", ");
}

export function IcpForm({
  campaignId,
  icp,
  missingFields,
  onSaved,
}: {
  campaignId: string;
  icp: ICP | null;
  missingFields?: string[];
  onSaved: (campaign: CampaignResponse) => void;
}) {
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<IcpFormInput, unknown, IcpFormValues>({
    resolver: zodResolver(icpFormSchema),
    defaultValues: {
      industries: toDisplayList(icp?.industries ?? []),
      locations: toDisplayList(icp?.locations ?? []),
      company_size_min: icp?.company_size_min ?? undefined,
      company_size_max: icp?.company_size_max ?? undefined,
      signals: toDisplayList(icp?.signals ?? []),
      exclusions: toDisplayList(icp?.exclusions ?? []),
      target_roles: toDisplayList(icp?.target_roles ?? []),
    },
  });

  const onSubmit = async (values: IcpFormValues) => {
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
          icp: {
            industries: values.industries,
            locations: values.locations,
            company_size_min: values.company_size_min ?? null,
            company_size_max: values.company_size_max ?? null,
            signals: values.signals,
            exclusions: values.exclusions,
            target_roles: values.target_roles,
          },
        },
        campaignResponseSchema,
        { accessToken },
      );
      onSaved(campaign);
    } catch (error) {
      setServerError(error instanceof ApiError ? error.message : "Could not save the ICP.");
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ideal customer profile</CardTitle>
      </CardHeader>
      <CardContent>
        {missingFields && missingFields.length > 0 && (
          <p
            role="alert"
            className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800"
          >
            The brief didn&apos;t specify enough detail to fill in: {missingFields.join(", ")}. Add
            it below.
          </p>
        )}
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="industries">Industries (comma-separated)</Label>
              <Input id="industries" {...register("industries")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="locations">Locations (comma-separated)</Label>
              <Input id="locations" {...register("locations")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="company_size_min">Company size — min</Label>
              <Input
                id="company_size_min"
                type="number"
                min={0}
                {...register("company_size_min")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="company_size_max">Company size — max</Label>
              <Input
                id="company_size_max"
                type="number"
                min={0}
                {...register("company_size_max")}
              />
              {errors.company_size_max && (
                <p role="alert" className="text-sm text-red-600">
                  {errors.company_size_max.message}
                </p>
              )}
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="signals">Buying signals (comma-separated)</Label>
              <Input id="signals" {...register("signals")} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="exclusions">Exclusions (comma-separated)</Label>
              <Input id="exclusions" {...register("exclusions")} />
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label htmlFor="target_roles">Target roles (comma-separated)</Label>
              <Input id="target_roles" {...register("target_roles")} />
            </div>
          </div>
          {serverError && (
            <p role="alert" className="text-sm text-red-600">
              {serverError}
            </p>
          )}
          <Button type="submit" variant="secondary" size="sm" disabled={isSubmitting}>
            {isSubmitting ? "Saving..." : "Save ICP"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
