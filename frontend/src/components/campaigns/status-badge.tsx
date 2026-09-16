import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { CampaignStatus } from "@/lib/types/api";

const STATUS_LABELS: Record<CampaignStatus, string> = {
  draft: "Draft",
  awaiting_plan_approval: "Awaiting approval",
  plan_approved: "Plan approved",
  queued: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  paused: "Paused",
};

const STATUS_VARIANTS: Record<CampaignStatus, BadgeProps["variant"]> = {
  draft: "neutral",
  awaiting_plan_approval: "warning",
  plan_approved: "success",
  queued: "brand",
  running: "brand",
  completed: "success",
  failed: "danger",
  paused: "warning",
};

const LIVE_STATUSES = new Set<CampaignStatus>(["queued", "running"]);

export function StatusBadge({ status }: { status: CampaignStatus }) {
  return (
    <Badge variant={STATUS_VARIANTS[status]} dot={LIVE_STATUSES.has(status)}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
