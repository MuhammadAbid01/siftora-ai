import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/cn";
import type { CampaignAnalyticsResponse } from "@/lib/types/api";

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "danger";
}) {
  return (
    <div>
      <dt className="text-sm text-slate-500 dark:text-slate-400">{label}</dt>
      <dd
        className={cn(
          "mt-0.5 text-2xl font-semibold tabular-nums",
          tone === "danger" && value !== "0"
            ? "text-red-600 dark:text-red-400"
            : "text-slate-900 dark:text-slate-100",
        )}
      >
        {value}
      </dd>
    </div>
  );
}

export function CampaignAnalytics({ analytics }: { analytics: CampaignAnalyticsResponse }) {
  const totalLeads =
    analytics.qualified_count + analytics.needs_review_count + analytics.rejected_count;

  return (
    <div className="space-y-6 motion-safe:animate-fade-in">
      <Card>
        <CardHeader>
          <CardTitle>Funnel</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            <Stat label="Leads evaluated" value={String(totalLeads)} />
            <Stat label="Qualified" value={String(analytics.qualified_count)} />
            <Stat label="Needs review" value={String(analytics.needs_review_count)} />
            <Stat label="Rejected" value={String(analytics.rejected_count)} />
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Outreach</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-6 sm:grid-cols-3">
            <Stat label="Drafts generated" value={String(analytics.drafts_generated)} />
            <Stat label="Approved" value={String(analytics.drafts_approved)} />
            <Stat label="Rejected" value={String(analytics.drafts_rejected)} />
          </dl>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Cost, latency, and failures</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-2 gap-6 sm:grid-cols-4">
            <Stat label="Runs" value={String(analytics.runs_count)} />
            <Stat label="Queries used" value={String(analytics.total_queries_used)} />
            <Stat label="Estimated cost" value={`$${analytics.total_cost_usd.toFixed(2)}`} />
            <Stat
              label="Avg tool latency"
              value={
                analytics.avg_tool_latency_ms === null
                  ? "—"
                  : `${Math.round(analytics.avg_tool_latency_ms)} ms`
              }
            />
            <Stat
              label="Tool-call failures"
              value={String(analytics.tool_call_failures)}
              tone="danger"
            />
            <Stat
              label="Agent-event failures"
              value={String(analytics.agent_event_failures)}
              tone="danger"
            />
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
