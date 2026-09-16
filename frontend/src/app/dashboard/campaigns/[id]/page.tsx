import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { campaignResponseSchema, type CampaignResponse } from "@/lib/types/api";
import { CampaignDetail } from "@/components/campaigns/campaign-detail";
import { Alert } from "@/components/ui/alert";

export const metadata: Metadata = {
  title: "Campaign",
};

type LoadResult = { campaign: CampaignResponse } | { notFound: true } | { errorMessage: string };

async function loadCampaign(id: string, accessToken: string): Promise<LoadResult> {
  try {
    const campaign = await apiGet(`/api/campaigns/${id}`, campaignResponseSchema, { accessToken });
    return { campaign };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { notFound: true };
    }
    const errorMessage =
      error instanceof ApiError
        ? `Could not load this campaign (${error.code}).`
        : "Could not load this campaign.";
    return { errorMessage };
  }
}

export default async function CampaignDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadCampaign(id, session.access_token);

  if ("notFound" in result) {
    notFound();
  }

  if ("errorMessage" in result) {
    return <Alert>{result.errorMessage}</Alert>;
  }

  return <CampaignDetail initialCampaign={result.campaign} />;
}
