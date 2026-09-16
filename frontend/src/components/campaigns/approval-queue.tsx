"use client";

import { useState } from "react";
import Link from "next/link";
import type { ApprovalResponse } from "@/lib/types/api";
import { OutreachDraftCard } from "@/components/campaigns/outreach-draft-card";
import { EmptyState } from "@/components/ui/empty-state";

export function ApprovalQueue({ initialApprovals }: { initialApprovals: ApprovalResponse[] }) {
  const [approvals, setApprovals] = useState(initialApprovals);

  const handleUpdated = (updated: ApprovalResponse) => {
    setApprovals((current) => current.map((a) => (a.id === updated.id ? updated : a)));
  };

  if (approvals.length === 0) {
    return (
      <EmptyState
        size="lg"
        icon={
          <svg width="28" height="28" viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path
              d="M4 9.5 8 13l8-8"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        }
        title="All caught up"
        description="No drafts are waiting for review right now — new ones will show up here as campaigns run."
      />
    );
  }

  return (
    <div className="space-y-4">
      {approvals.map((approval, index) => (
        <div
          key={approval.id}
          className="space-y-1 motion-safe:animate-fade-in-up"
          style={{ animationDelay: `${Math.min(index, 6) * 50}ms` }}
        >
          <Link
            href={`/dashboard/campaigns/${approval.campaign_id}/leads/${approval.lead_id}`}
            className="inline-flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            View lead
            <svg width="10" height="10" viewBox="0 0 12 12" fill="none" aria-hidden="true">
              <path
                d="M4 8 8 4M8 4H4.5M8 4v3.5"
                stroke="currentColor"
                strokeWidth="1.3"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>
          <OutreachDraftCard approval={approval} onUpdated={handleUpdated} />
        </div>
      ))}
    </div>
  );
}
