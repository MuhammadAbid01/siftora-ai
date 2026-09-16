import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { campaignListResponseSchema, type CampaignResponse } from "@/lib/types/api";
import { CampaignsBrowser } from "@/components/campaigns/campaigns-browser";
import { Alert } from "@/components/ui/alert";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export const metadata: Metadata = {
  title: "Campaigns",
};

async function loadCampaigns(
  accessToken: string,
): Promise<{ campaigns: CampaignResponse[] } | { errorMessage: string }> {
  try {
    const result = await apiGet("/api/campaigns", campaignListResponseSchema, { accessToken });
    return { campaigns: result.items };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? `Could not load campaigns (${error.code}).`
        : "Could not load campaigns.";
    return { errorMessage };
  }
}

export default async function CampaignsPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadCampaigns(session.access_token);

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Campaigns
        </h1>
        <Link href="/dashboard/campaigns/new" className={cn(buttonVariants({ size: "sm" }))}>
          New campaign
        </Link>
      </div>

      {"errorMessage" in result && <Alert>{result.errorMessage}</Alert>}

      {"campaigns" in result && <CampaignsBrowser campaigns={result.campaigns} />}
    </div>
  );
}
