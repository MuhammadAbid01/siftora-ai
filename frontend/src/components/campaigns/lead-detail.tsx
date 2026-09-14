"use client";

import { useState } from "react";
import { apiPost, ApiError } from "@/lib/api-client";
import {
  approvalResponseSchema,
  leadDetailWithApprovalsResponseSchema,
  type ApprovalResponse,
  type LeadDetailWithApprovalsResponse,
} from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { LeadStatusBadge } from "@/components/campaigns/lead-status-badge";
import { EvidenceList } from "@/components/campaigns/evidence-list";
import { ScoreBreakdownTable } from "@/components/campaigns/score-breakdown-table";
import { OutreachDraftCard } from "@/components/campaigns/outreach-draft-card";
import { Button } from "@/components/ui/button";

export function LeadDetail({ initialLead }: { initialLead: LeadDetailWithApprovalsResponse }) {
  const [lead, setLead] = useState(initialLead);
  const [rescoring, setRescoring] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outreachError, setOutreachError] = useState<string | null>(null);

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
      const updated = await apiPost(
        `/api/leads/${lead.id}/rescore`,
        {},
        leadDetailWithApprovalsResponseSchema,
        { accessToken },
      );
      setLead(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not rescore this lead.");
    } finally {
      setRescoring(false);
    }
  };

  const handleGenerateOutreach = async () => {
    setGenerating(true);
    setOutreachError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setOutreachError("Your session has expired. Please sign in again.");
      setGenerating(false);
      return;
    }

    try {
      const created = await apiPost(
        `/api/leads/${lead.id}/regenerate-outreach`,
        { channel: "email" },
        approvalResponseSchema,
        { accessToken },
      );
      setLead((current) => ({ ...current, approvals: [created, ...current.approvals] }));
    } catch (err) {
      setOutreachError(
        err instanceof ApiError ? err.message : "Could not generate an outreach draft.",
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleApprovalUpdated = (updated: ApprovalResponse) => {
    setLead((current) => ({
      ...current,
      approvals: current.approvals.map((a) => (a.id === updated.id ? updated : a)),
    }));
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

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-slate-900">Outreach</h2>
          {lead.status === "qualified" && (
            <Button size="sm" onClick={() => void handleGenerateOutreach()} disabled={generating}>
              {generating
                ? "Generating..."
                : lead.approvals.length > 0
                  ? "Regenerate draft"
                  : "Generate email draft"}
            </Button>
          )}
        </div>
        {lead.status !== "qualified" && (
          <p className="text-sm text-slate-500">
            Only qualified leads can receive outreach drafts.
          </p>
        )}
        {outreachError && (
          <p role="alert" className="text-sm text-red-600">
            {outreachError}
          </p>
        )}
        {lead.approvals.map((approval) => (
          <OutreachDraftCard
            key={approval.id}
            approval={approval}
            onUpdated={handleApprovalUpdated}
          />
        ))}
      </div>
    </div>
  );
}
