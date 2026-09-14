import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { campaignListResponseSchema, type CampaignResponse } from "@/lib/types/api";
import { CampaignList } from "@/components/campaigns/campaign-list";
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
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        Your session could not be verified. Please sign in again.
      </div>
    );
  }

  const result = await loadCampaigns(session.access_token);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-slate-900">Campaigns</h1>
        <Link href="/dashboard/campaigns/new" className={cn(buttonVariants({ size: "sm" }))}>
          New campaign
        </Link>
      </div>

      {"errorMessage" in result && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
        >
          {result.errorMessage}
        </div>
      )}

      {"campaigns" in result && result.campaigns.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
          No campaigns yet.{" "}
          <Link
            href="/dashboard/campaigns/new"
            className="font-medium text-indigo-600 hover:text-indigo-500"
          >
            Create your first one
          </Link>
          .
        </div>
      )}

      {"campaigns" in result && result.campaigns.length > 0 && (
        <CampaignList campaigns={result.campaigns} />
      )}
    </div>
  );
}
