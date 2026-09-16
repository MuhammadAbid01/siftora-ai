import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { campaignAnalyticsResponseSchema, type CampaignAnalyticsResponse } from "@/lib/types/api";
import { CampaignAnalytics } from "@/components/campaigns/campaign-analytics";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";

export const metadata: Metadata = {
  title: "Analytics",
};

type LoadResult =
  { analytics: CampaignAnalyticsResponse } | { neverRun: true } | { errorMessage: string };

async function loadAnalytics(campaignId: string, accessToken: string): Promise<LoadResult> {
  try {
    const analytics = await apiGet(
      `/api/campaigns/${campaignId}/analytics`,
      campaignAnalyticsResponseSchema,
      { accessToken },
    );
    return { analytics };
  } catch (error) {
    if (error instanceof ApiError && error.code === "no_run_yet") {
      return { neverRun: true };
    }
    const errorMessage =
      error instanceof ApiError
        ? `Could not load analytics (${error.code}).`
        : "Could not load analytics.";
    return { errorMessage };
  }
}

export default async function CampaignAnalyticsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadAnalytics(id, session.access_token);

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Analytics
        </h1>
        <Link
          href={`/dashboard/campaigns/${id}`}
          className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
        >
          Back to campaign
        </Link>
      </div>

      {"errorMessage" in result && <Alert>{result.errorMessage}</Alert>}

      {"neverRun" in result && (
        <EmptyState
          title="No analytics yet"
          description="This campaign has not been run yet — analytics appear once a run completes."
        />
      )}

      {"analytics" in result && <CampaignAnalytics analytics={result.analytics} />}
    </div>
  );
}
