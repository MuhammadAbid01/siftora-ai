"use client";

import { useState } from "react";
import Link from "next/link";
import type { ApprovalResponse } from "@/lib/types/api";
import { OutreachDraftCard } from "@/components/campaigns/outreach-draft-card";

export function ApprovalQueue({ initialApprovals }: { initialApprovals: ApprovalResponse[] }) {
  const [approvals, setApprovals] = useState(initialApprovals);

  const handleUpdated = (updated: ApprovalResponse) => {
    setApprovals((current) => current.map((a) => (a.id === updated.id ? updated : a)));
  };

  if (approvals.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-6 text-sm text-slate-500">
        No drafts waiting for review.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {approvals.map((approval) => (
        <div key={approval.id} className="space-y-1">
          <Link
            href={`/dashboard/campaigns/${approval.campaign_id}/leads/${approval.lead_id}`}
            className="text-xs text-indigo-600 hover:text-indigo-500"
          >
            View lead
          </Link>
          <OutreachDraftCard approval={approval} onUpdated={handleUpdated} />
        </div>
      ))}
    </div>
  );
}
