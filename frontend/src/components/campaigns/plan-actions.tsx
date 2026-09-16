"use client";

import { useState } from "react";
import { apiPost, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

export function PlanActions({
  campaign,
  onUpdated,
  onIcpIncomplete,
}: {
  campaign: CampaignResponse;
  onUpdated: (campaign: CampaignResponse) => void;
  onIcpIncomplete: (missingFields: string[]) => void;
}) {
  const [pendingAction, setPendingAction] = useState<"plan" | "confirm-plan" | "run" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runAction = async (action: "plan" | "confirm-plan" | "run") => {
    setError(null);
    setPendingAction(action);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
      setPendingAction(null);
      return;
    }

    try {
      const updated = await apiPost(
        `/api/campaigns/${campaign.id}/${action}`,
        {},
        campaignResponseSchema,
        { accessToken },
      );
      onUpdated(updated);
    } catch (err) {
      if (err instanceof ApiError && err.code === "icp_incomplete") {
        const missingFields = (err.details?.missing_fields as string[] | undefined) ?? [];
        onIcpIncomplete(missingFields);
        setError(err.message);
      } else if (
        err instanceof ApiError &&
        (err.code === "plan_generation_failed" || err.code === "plan_provider_unavailable")
      ) {
        // The API already phrases these for the user (retry vs. add more
        // detail to the brief) — show that, never the raw provider error,
        // which stays in `details.reason` and the backend logs.
        setError(err.message);
      } else {
        setError(err instanceof ApiError ? err.message : "That action could not be completed.");
      }
    } finally {
      setPendingAction(null);
    }
  };

  // A complete ICP alone isn't enough to approve — a user can fill in
  // missing ICP fields by hand after an icp_incomplete response without
  // ever regenerating the search plan itself (the backend enforces this
  // too; this just keeps the button's disabled state honest about it).
  const hasCompleteIcp = Boolean(campaign.icp?.industries.length && campaign.icp?.locations.length);
  const hasSearchPlan = Boolean(campaign.search_plan?.length);
  const canConfirmPlan = hasCompleteIcp && hasSearchPlan;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3">
        <Button size="sm" onClick={() => void runAction("plan")} disabled={pendingAction !== null}>
          {pendingAction === "plan" ? "Generating..." : "Generate plan"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => void runAction("confirm-plan")}
          disabled={pendingAction !== null || !canConfirmPlan}
        >
          {pendingAction === "confirm-plan" ? "Confirming..." : "Confirm plan"}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => void runAction("run")}
          disabled={pendingAction !== null || campaign.status !== "plan_approved"}
        >
          {pendingAction === "run" ? "Starting..." : "Start run"}
        </Button>
      </div>
      {error && <Alert>{error}</Alert>}
    </div>
  );
}
