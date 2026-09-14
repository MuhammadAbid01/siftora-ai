"use client";

import { useState } from "react";
import { apiPost, ApiError } from "@/lib/api-client";
import { leadDetailResponseSchema, type LeadDetailResponse } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { LeadStatusBadge } from "@/components/campaigns/lead-status-badge";
import { EvidenceList } from "@/components/campaigns/evidence-list";
import { ScoreBreakdownTable } from "@/components/campaigns/score-breakdown-table";
import { Button } from "@/components/ui/button";

export function LeadDetail({ initialLead }: { initialLead: LeadDetailResponse }) {
  const [lead, setLead] = useState(initialLead);
  const [rescoring, setRescoring] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRescore = async () => {
    setRescoring(true);
    setError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
      setRescoring(false);
      return;
    }

    try {
      const updated = await apiPost(`/api/leads/${lead.id}/rescore`, {}, leadDetailResponseSchema, {
        accessToken,
      });
      setLead(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rescore this lead.");
    } finally {
      setRescoring(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">{lead.company.name}</h1>
          <p className="mt-1 text-sm text-slate-500">{lead.company.domain}</p>
          <a
            href={lead.source_url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-xs text-indigo-600 hover:text-indigo-500"
          >
            {lead.source_url}
          </a>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-lg font-semibold text-slate-900">{lead.score}/100</span>
          <LeadStatusBadge status={lead.status} />
        </div>
      </div>

      {lead.decision_reason && (
        <p className="rounded-md border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">
          Reason: {lead.decision_reason}
        </p>
      )}

      <div>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => void handleRescore()}
          disabled={rescoring}
        >
          {rescoring ? "Rescoring..." : "Rescore with current weights"}
        </Button>
        {error && (
          <p role="alert" className="mt-2 text-sm text-red-600">
            {error}
          </p>
        )}
      </div>

      <ScoreBreakdownTable breakdown={lead.score_breakdown} />
      <EvidenceList evidence={lead.evidence} />
    </div>
  );
}
