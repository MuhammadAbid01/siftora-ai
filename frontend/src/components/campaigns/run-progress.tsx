"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { apiGet, apiPost, ApiError } from "@/lib/api-client";
import {
  campaignRunResponseSchema,
  campaignResponseSchema,
  type CampaignRunResponse,
} from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";

const ACTIVE_RUN_STATUSES = new Set(["queued", "running"]);
const TERMINAL_RUN_STATUSES = new Set(["completed", "failed", "paused"]);

const RUN_STATUS_STYLES: Record<string, string> = {
  queued: "bg-indigo-50 text-indigo-700 border-indigo-200",
  running: "bg-indigo-50 text-indigo-700 border-indigo-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  failed: "bg-red-50 text-red-700 border-red-200",
  paused: "bg-amber-50 text-amber-800 border-amber-200",
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs text-slate-500">{label}</dt>
      <dd className="text-lg font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

export function RunProgress({
  campaignId,
  campaignStatus,
}: {
  campaignId: string;
  campaignStatus: string;
}) {
  const router = useRouter();
  const [progress, setProgress] = useState<CampaignRunResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pausing, setPausing] = useState(false);
  const previousStatus = useRef<string | null>(null);

  const fetchProgress = useCallback(async () => {
    const accessToken = await getAccessToken();
    if (!accessToken) return;

    try {
      const result = await apiGet(
        `/api/campaigns/${campaignId}/progress`,
        campaignRunResponseSchema,
        {
          accessToken,
        },
      );
      setProgress(result);
      setError(null);

      if (
        previousStatus.current &&
        !TERMINAL_RUN_STATUSES.has(previousStatus.current) &&
        TERMINAL_RUN_STATUSES.has(result.status)
      ) {
        router.refresh();
      }
      previousStatus.current = result.status;
    } catch (err) {
      if (err instanceof ApiError && err.code === "no_run_yet") {
        setProgress(null);
      } else {
        setError(err instanceof ApiError ? err.message : "Could not load run progress.");
      }
    } finally {
      setLoading(false);
    }
  }, [campaignId, router]);

  useEffect(() => {
    // Legitimate fetch-on-mount-and-poll pattern: fetchProgress sets state
    // asynchronously after awaiting the network call, not synchronously
    // within this effect body.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchProgress();
    if (!ACTIVE_RUN_STATUSES.has(campaignStatus)) {
      return;
    }
    const interval = setInterval(() => void fetchProgress(), 3000);
    return () => clearInterval(interval);
  }, [fetchProgress, campaignStatus]);

  const handlePause = async () => {
    setPausing(true);
    setError(null);
    const accessToken = await getAccessToken();
    if (!accessToken) {
      setError("Your session has expired. Please sign in again.");
      setPausing(false);
      return;
    }

    try {
      await apiPost(`/api/campaigns/${campaignId}/pause`, {}, campaignResponseSchema, {
        accessToken,
      });
      await fetchProgress();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not pause the run.");
    } finally {
      setPausing(false);
    }
  };

  if (loading) {
    return <div className="h-32 w-full animate-pulse rounded-lg bg-slate-200" />;
  }

  if (!progress) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Run progress</CardTitle>
          <div className="flex items-center gap-3">
            <span
              className={cn(
                "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
                RUN_STATUS_STYLES[progress.status],
              )}
            >
              {progress.status}
            </span>
            {ACTIVE_RUN_STATUSES.has(progress.status) && (
              <Button
                size="sm"
                variant="secondary"
                onClick={() => void handlePause()}
                disabled={pausing}
              >
                {pausing ? "Pausing..." : "Pause"}
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <Stat label="Queries used" value={progress.queries_used} />
          <Stat label="Leads created" value={progress.leads_created} />
          <Stat label="Qualified" value={progress.qualified_count} />
          <Stat label="Needs review" value={progress.needs_review_count} />
          <Stat label="Rejected" value={progress.rejected_count} />
          <Stat label="Failed" value={progress.failed_count} />
          <Stat label="Est. cost" value={`$${progress.estimated_cost_usd.toFixed(2)}`} />
        </dl>
        {progress.stop_reason && (
          <p className="mt-4 text-sm text-slate-500">Stopped: {progress.stop_reason}</p>
        )}
        {progress.error && (
          <p role="alert" className="mt-2 text-sm text-red-600">
            {progress.error}
          </p>
        )}
        {error && (
          <p role="alert" className="mt-2 text-sm text-red-600">
            {error}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
