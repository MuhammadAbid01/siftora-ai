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
import { Alert } from "@/components/ui/alert";
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
    <div className="space-y-6 motion-safe:animate-fade-in">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            {lead.company.name}
          </h1>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{lead.company.domain}</p>
          <a
            href={lead.source_url}
            target="_blank"
            rel="noreferrer"
            className="mt-1 inline-block text-xs text-indigo-600 hover:text-indigo-500 dark:text-indigo-400 dark:hover:text-indigo-300"
          >
            {lead.source_url}
          </a>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-2xl font-semibold tabular-nums text-slate-900 dark:text-slate-100">
            {lead.score}
            <span className="text-sm font-normal text-slate-400 dark:text-slate-500">/100</span>
          </span>
          <LeadStatusBadge status={lead.status} />
        </div>
      </div>

      {lead.decision_reason && (
        <p className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600 dark:border-slate-800 dark:bg-slate-900/60 dark:text-slate-400">
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
        {error && <Alert className="mt-2">{error}</Alert>}
      </div>

      <ScoreBreakdownTable breakdown={lead.score_breakdown} />
      <EvidenceList evidence={lead.evidence} />

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Outreach
          </h2>
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
          <p className="text-sm text-slate-500 dark:text-slate-400">
            Only qualified leads can receive outreach drafts.
          </p>
        )}
        {outreachError && <Alert>{outreachError}</Alert>}
        {lead.approvals.map((approval, index) => (
          <div
            key={approval.id}
            className="motion-safe:animate-fade-in-up"
            style={{ animationDelay: `${Math.min(index, 4) * 60}ms` }}
          >
            <OutreachDraftCard approval={approval} onUpdated={handleApprovalUpdated} />
          </div>
        ))}
      </div>
    </div>
  );
}
