import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { leadListResponseSchema, type LeadSummaryResponse } from "@/lib/types/api";
import { LeadList } from "@/components/campaigns/lead-list";
import { Alert } from "@/components/ui/alert";
import { EmptyState } from "@/components/ui/empty-state";

export const metadata: Metadata = {
  title: "Leads",
};

async function loadLeads(
  campaignId: string,
  accessToken: string,
): Promise<{ leads: LeadSummaryResponse[] } | { errorMessage: string }> {
  try {
    const result = await apiGet(
      `/api/campaigns/${campaignId}/leads?limit=100`,
      leadListResponseSchema,
      {
        accessToken,
      },
    );
    return { leads: result.items };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError ? `Could not load leads (${error.code}).` : "Could not load leads.";
    return { errorMessage };
  }
}

export default async function LeadsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadLeads(id, session.access_token);

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Leads
        </h1>
        <Link
          href={`/dashboard/campaigns/${id}`}
          className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
        >
          Back to campaign
        </Link>
      </div>

      {"errorMessage" in result && <Alert>{result.errorMessage}</Alert>}

      {"leads" in result && result.leads.length === 0 && (
        <EmptyState
          title="No leads yet"
          description="Start a run from the campaign page to discover some."
        />
      )}

      {"leads" in result && result.leads.length > 0 && (
        <LeadList campaignId={id} leads={result.leads} />
      )}
    </div>
  );
}
