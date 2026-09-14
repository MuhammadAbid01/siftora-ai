"use client";

import { useState } from "react";
import { apiPatch, apiPost, ApiError } from "@/lib/api-client";
import { approvalResponseSchema, type ApprovalResponse } from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { ApprovalStatusBadge } from "@/components/campaigns/approval-status-badge";
import { QualityStatusBadge } from "@/components/campaigns/quality-status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function OutreachDraftCard({
  approval,
  onUpdated,
}: {
  approval: ApprovalResponse;
  onUpdated: (updated: ApprovalResponse) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [subject, setSubject] = useState(approval.draft.subject);
  const [body, setBody] = useState(approval.draft.body);
  const [busy, setBusy] = useState<"approve" | "reject" | "save" | null>(null);
  const [error, setError] = useState<string | null>(null);

  const withToken = async (): Promise<string | null> => {
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
    }
    return accessToken;
  };

  const handleApprove = async () => {
    setBusy("approve");
    setError(null);
    const accessToken = await withToken();
    if (!accessToken) {
      setBusy(null);
      return;
    }
    try {
      const updated = await apiPost(
        `/api/approvals/${approval.id}/approve`,
        {},
        approvalResponseSchema,
        { accessToken },
      );
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not approve this draft.");
    } finally {
      setBusy(null);
    }
  };

  const handleReject = async () => {
    setBusy("reject");
    setError(null);
    const accessToken = await withToken();
    if (!accessToken) {
      setBusy(null);
      return;
    }
    try {
      const updated = await apiPost(
        `/api/approvals/${approval.id}/reject`,
        {},
        approvalResponseSchema,
        { accessToken },
      );
      onUpdated(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not reject this draft.");
    } finally {
      setBusy(null);
    }
  };

  const handleSaveEdit = async () => {
    setBusy("save");
    setError(null);
    const accessToken = await withToken();
    if (!accessToken) {
      setBusy(null);
      return;
    }
    try {
      const updated = await apiPatch(
        `/api/approvals/${approval.id}/draft`,
        { subject, body },
        approvalResponseSchema,
        { accessToken },
      );
      onUpdated(updated);
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not save this edit.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle>
            {approval.company.name} — {approval.draft.channel} (v{approval.draft.version})
          </CardTitle>
          <div className="flex items-center gap-2">
            <QualityStatusBadge status={approval.draft.quality_status} />
            <ApprovalStatusBadge status={approval.status} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {editing ? (
          <div className="space-y-3">
            <Input
              aria-label="Subject"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
            <Textarea
              aria-label="Body"
              rows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
            />
            <div className="flex gap-2">
              <Button size="sm" onClick={() => void handleSaveEdit()} disabled={busy === "save"}>
                {busy === "save" ? "Saving..." : "Save edit"}
              </Button>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setSubject(approval.draft.subject);
                  setBody(approval.draft.body);
                  setEditing(false);
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            <p className="text-sm font-medium text-slate-900">{approval.draft.subject}</p>
            <p className="whitespace-pre-line text-sm text-slate-700">{approval.draft.body}</p>
          </div>
        )}

        {!editing && (
          <div className="flex flex-wrap gap-2 pt-2">
            <Button
              size="sm"
              onClick={() => void handleApprove()}
              disabled={busy !== null || approval.status === "approved"}
            >
              {busy === "approve" ? "Approving..." : "Approve"}
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => void handleReject()}
              disabled={busy !== null || approval.status === "rejected"}
            >
              {busy === "reject" ? "Rejecting..." : "Reject"}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setEditing(true)}
              disabled={busy !== null}
            >
              Edit
            </Button>
          </div>
        )}

        {error && (
          <p role="alert" className="text-sm text-red-600">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
