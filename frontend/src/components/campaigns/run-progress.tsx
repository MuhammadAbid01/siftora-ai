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
import { Alert } from "@/components/ui/alert";
import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const ACTIVE_RUN_STATUSES = new Set(["queued", "running"]);
const TERMINAL_RUN_STATUSES = new Set(["completed", "failed", "paused"]);

const RUN_STATUS_VARIANTS: Record<string, BadgeProps["variant"]> = {
  queued: "brand",
  running: "brand",
  completed: "success",
  failed: "danger",
  paused: "warning",
};

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <dt className="text-xs text-slate-500 dark:text-slate-400">{label}</dt>
      <dd className="mt-0.5 text-lg font-semibold tabular-nums text-slate-900 dark:text-slate-100">
        {value}
      </dd>
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
    return <Skeleton className="h-32 w-full" />;
  }

  if (!progress) {
    return null;
  }

  return (
    <Card className="motion-safe:animate-fade-in">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>Run progress</CardTitle>
          <div className="flex items-center gap-3">
            <Badge
              variant={RUN_STATUS_VARIANTS[progress.status]}
              dot={ACTIVE_RUN_STATUSES.has(progress.status)}
            >
              {progress.status}
            </Badge>
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
          <p className="mt-4 text-sm text-slate-500 dark:text-slate-400">
            Stopped: {progress.stop_reason}
          </p>
        )}
        {progress.error && (
          <Alert className="mt-3" variant="error">
            {progress.error}
          </Alert>
        )}
        {error && (
          <Alert className="mt-3" variant="error">
            {error}
          </Alert>
        )}
      </CardContent>
    </Card>
  );
}
