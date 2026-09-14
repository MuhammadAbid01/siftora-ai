"use client";

import { useState } from "react";
import Link from "next/link";
import { StatusBadge } from "@/components/campaigns/status-badge";
import { IcpForm } from "@/components/campaigns/icp-form";
import { SearchPlanList } from "@/components/campaigns/search-plan-list";
import { ScoreWeightsForm } from "@/components/campaigns/score-weights-form";
import { ScoreThresholdsForm } from "@/components/campaigns/score-thresholds-form";
import { RunLimitsForm } from "@/components/campaigns/run-limits-form";
import { SenderForm } from "@/components/campaigns/sender-form";
import { ExportButton } from "@/components/campaigns/export-button";
import { PlanActions } from "@/components/campaigns/plan-actions";
import { RunProgress } from "@/components/campaigns/run-progress";
import { EventTimeline } from "@/components/campaigns/event-timeline";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import type { CampaignResponse } from "@/lib/types/api";

export function CampaignDetail({ initialCampaign }: { initialCampaign: CampaignResponse }) {
  const [campaign, setCampaign] = useState(initialCampaign);
  const [syncedCampaign, setSyncedCampaign] = useState(initialCampaign);
  const [missingFields, setMissingFields] = useState<string[]>([]);

  // A completed/failed/paused run triggers router.refresh() (see
  // RunProgress), which re-renders this component's server parent with a
  // new `initialCampaign` prop — useState's initial value is only used on
  // first mount, so without this the fresh data would never reach local
  // state. This is React's documented "adjust state during render" pattern
  // (not an effect) for resetting state when a prop changes.
  if (initialCampaign !== syncedCampaign) {
    setSyncedCampaign(initialCampaign);
    setCampaign(initialCampaign);
  }

  const handleUpdated = (updated: CampaignResponse) => {
    setCampaign(updated);
    setMissingFields([]);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Campaign</h1>
          <p className="mt-1 max-w-2xl text-sm text-slate-600">{campaign.brief}</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={campaign.status} />
          <Link
            href={`/dashboard/campaigns/${campaign.id}/leads`}
            className={cn(buttonVariants({ variant: "secondary", size: "sm" }))}
          >
            View leads
          </Link>
          <ExportButton campaignId={campaign.id} />
        </div>
      </div>

      <PlanActions
        campaign={campaign}
        onUpdated={handleUpdated}
        onIcpIncomplete={setMissingFields}
      />

      <RunProgress campaignId={campaign.id} campaignStatus={campaign.status} />

      <IcpForm
        campaignId={campaign.id}
        icp={campaign.icp}
        missingFields={missingFields}
        onSaved={handleUpdated}
      />

      <SearchPlanList searchPlan={campaign.search_plan} />

      <ScoreWeightsForm
        campaignId={campaign.id}
        weights={campaign.score_weights}
        onSaved={handleUpdated}
      />

      <ScoreThresholdsForm
        campaignId={campaign.id}
        thresholds={campaign.score_thresholds}
        onSaved={handleUpdated}
      />

      <RunLimitsForm campaignId={campaign.id} limits={campaign.limits} onSaved={handleUpdated} />

      <SenderForm
        campaignId={campaign.id}
        senderName={campaign.sender_name}
        senderEmail={campaign.sender_email}
        onSaved={handleUpdated}
      />

      <EventTimeline campaignId={campaign.id} campaignStatus={campaign.status} />
    </div>
  );
}
