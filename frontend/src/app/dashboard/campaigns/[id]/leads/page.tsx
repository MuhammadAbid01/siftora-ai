import type { Metadata } from "next";
import Link from "next/link";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { leadListResponseSchema, type LeadSummaryResponse } from "@/lib/types/api";
import { LeadList } from "@/components/campaigns/lead-list";

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
    return (
      <div
        role="alert"
        className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
      >
        Your session could not be verified. Please sign in again.
      </div>
    );
  }

  const result = await loadLeads(id, session.access_token);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Leads</h1>
          <Link
            href={`/dashboard/campaigns/${id}`}
            className="text-sm text-indigo-600 hover:text-indigo-500"
          >
            Back to campaign
          </Link>
        </div>
      </div>

      {"errorMessage" in result && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 p-6 text-sm text-red-700"
        >
          {result.errorMessage}
        </div>
      )}

      {"leads" in result && result.leads.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
          No leads yet. Start a run from the campaign page to discover some.
        </div>
      )}

      {"leads" in result && result.leads.length > 0 && (
        <LeadList campaignId={id} leads={result.leads} />
      )}
    </div>
  );
}
