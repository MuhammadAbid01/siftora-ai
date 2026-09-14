"use client";

import { useCallback, useEffect, useState } from "react";
import { apiGet, ApiError } from "@/lib/api-client";
import {
  agentEventListResponseSchema,
  campaignRunResponseSchema,
  toolCallListResponseSchema,
  type AgentEventResponse,
  type ToolCallResponse,
} from "@/lib/types/api";
import { getAccessToken } from "@/lib/supabase/access-token";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const ACTIVE_STATUSES = new Set(["queued", "running"]);

type TimelineItem =
  | { kind: "event"; at: string; data: AgentEventResponse }
  | { kind: "tool_call"; at: string; data: ToolCallResponse };

export function EventTimeline({
  campaignId,
  campaignStatus,
}: {
  campaignId: string;
  campaignStatus: string;
}) {
  const [items, setItems] = useState<TimelineItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchTimeline = useCallback(async () => {
    const accessToken = await getAccessToken();
    if (!accessToken) return;

    try {
      const progress = await apiGet(
        `/api/campaigns/${campaignId}/progress`,
        campaignRunResponseSchema,
        {
          accessToken,
        },
      );

      const [events, toolCalls] = await Promise.all([
        apiGet(`/api/runs/${progress.id}/events?limit=50`, agentEventListResponseSchema, {
          accessToken,
        }),
        apiGet(`/api/runs/${progress.id}/tool-calls?limit=50`, toolCallListResponseSchema, {
          accessToken,
        }),
      ]);

      const merged: TimelineItem[] = [
        ...events.items.map((e): TimelineItem => ({ kind: "event", at: e.created_at, data: e })),
        ...toolCalls.items.map((t): TimelineItem => ({
          kind: "tool_call",
          at: t.created_at,
          data: t,
        })),
      ].sort((a, b) => (a.at < b.at ? 1 : -1));

      setItems(merged);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.code === "no_run_yet") {
        setItems(null);
      } else {
        setError(err instanceof ApiError ? err.message : "Could not load the run timeline.");
      }
    }
  }, [campaignId]);

  useEffect(() => {
    // Legitimate fetch-on-mount-and-poll pattern: fetchTimeline sets state
    // asynchronously after awaiting the network calls, not synchronously
    // within this effect body.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchTimeline();
    if (!ACTIVE_STATUSES.has(campaignStatus)) {
      return;
    }
    const interval = setInterval(() => void fetchTimeline(), 3000);
    return () => clearInterval(interval);
  }, [fetchTimeline, campaignStatus]);

  if (error) {
    return (
      <p role="alert" className="text-sm text-red-600">
        {error}
      </p>
    );
  }

  if (!items || items.length === 0) {
    return null;
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Activity</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="max-h-96 space-y-2 overflow-y-auto text-sm">
          {items.map((item) => (
            <li
              key={`${item.kind}-${item.data.id}`}
              className="flex items-start justify-between gap-3 border-b border-slate-100 pb-2 last:border-0"
            >
              <div>
                <span className="font-mono text-xs text-slate-400">
                  {item.kind === "event"
                    ? item.data.node
                    : `${item.data.tool} (${item.data.provider})`}
                </span>
                <p className={item.data.status === "error" ? "text-red-600" : "text-slate-700"}>
                  {item.data.summary}
                </p>
              </div>
              <span className="shrink-0 text-xs text-slate-400">
                {new Date(item.at).toLocaleTimeString()}
              </span>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
