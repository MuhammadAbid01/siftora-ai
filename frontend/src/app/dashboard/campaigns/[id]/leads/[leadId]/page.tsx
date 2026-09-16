import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import {
  leadDetailWithApprovalsResponseSchema,
  type LeadDetailWithApprovalsResponse,
} from "@/lib/types/api";
import { LeadDetail } from "@/components/campaigns/lead-detail";
import { Alert } from "@/components/ui/alert";

export const metadata: Metadata = {
  title: "Lead",
};

type LoadResult =
  { lead: LeadDetailWithApprovalsResponse } | { notFound: true } | { errorMessage: string };

async function loadLead(leadId: string, accessToken: string): Promise<LoadResult> {
  try {
    const lead = await apiGet(`/api/leads/${leadId}`, leadDetailWithApprovalsResponseSchema, {
      accessToken,
    });
    return { lead };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { notFound: true };
    }
    const errorMessage =
      error instanceof ApiError
        ? `Could not load this lead (${error.code}).`
        : "Could not load this lead.";
    return { errorMessage };
  }
}

export default async function LeadDetailPage({
  params,
}: {
  params: Promise<{ id: string; leadId: string }>;
}) {
  const { id, leadId } = await params;
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadLead(leadId, session.access_token);

  if ("notFound" in result) {
    notFound();
  }

  if ("errorMessage" in result) {
    return <Alert>{result.errorMessage}</Alert>;
  }

  return (
    <div className="space-y-4 motion-safe:animate-fade-in">
      <Link
        href={`/dashboard/campaigns/${id}/leads`}
        className="text-sm text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
      >
        Back to leads
      </Link>
      <LeadDetail initialLead={result.lead} />
    </div>
  );
}
