import type { Metadata } from "next";
import { createClient } from "@/lib/supabase/server";
import { apiGet, ApiError } from "@/lib/api-client";
import { approvalListResponseSchema, type ApprovalResponse } from "@/lib/types/api";
import { ApprovalQueue } from "@/components/campaigns/approval-queue";
import { Alert } from "@/components/ui/alert";

export const metadata: Metadata = {
  title: "Approvals",
};

async function loadApprovals(
  accessToken: string,
): Promise<{ approvals: ApprovalResponse[] } | { errorMessage: string }> {
  try {
    const result = await apiGet(
      "/api/approvals?status=pending&limit=100",
      approvalListResponseSchema,
      { accessToken },
    );
    return { approvals: result.items };
  } catch (error) {
    const errorMessage =
      error instanceof ApiError
        ? `Could not load approvals (${error.code}).`
        : "Could not load approvals.";
    return { errorMessage };
  }
}

export default async function ApprovalsPage() {
  const supabase = await createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (!session) {
    return <Alert>Your session could not be verified. Please sign in again.</Alert>;
  }

  const result = await loadApprovals(session.access_token);

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Approvals
        </h1>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Drafts awaiting your review, across every campaign.
        </p>
      </div>

      {"errorMessage" in result && <Alert>{result.errorMessage}</Alert>}

      {"approvals" in result && <ApprovalQueue initialApprovals={result.approvals} />}
    </div>
  );
}
