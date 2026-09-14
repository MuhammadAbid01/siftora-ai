import { cn } from "@/lib/cn";
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

const STATUS_STYLES: Record<CampaignStatus, string> = {
  draft: "bg-slate-100 text-slate-700 border-slate-200",
  awaiting_plan_approval: "bg-amber-50 text-amber-800 border-amber-200",
  plan_approved: "bg-emerald-50 text-emerald-700 border-emerald-200",
  queued: "bg-indigo-50 text-indigo-700 border-indigo-200",
  running: "bg-indigo-50 text-indigo-700 border-indigo-200",
  completed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  failed: "bg-red-50 text-red-700 border-red-200",
  paused: "bg-amber-50 text-amber-800 border-amber-200",
};

export function StatusBadge({ status }: { status: CampaignStatus }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium",
        STATUS_STYLES[status],
      )}
    >
      {STATUS_LABELS[status]}
    </span>
  );
}
