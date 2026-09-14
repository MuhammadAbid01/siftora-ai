import { cn } from "@/lib/cn";
import type { LeadStatus } from "@/lib/types/api";

const STATUS_LABELS: Record<LeadStatus, string> = {
  qualified: "Qualified",
  needs_review: "Needs review",
  rejected: "Rejected",
};

const STATUS_STYLES: Record<LeadStatus, string> = {
  qualified: "bg-emerald-50 text-emerald-700 border-emerald-200",
  needs_review: "bg-amber-50 text-amber-800 border-amber-200",
  rejected: "bg-slate-100 text-slate-600 border-slate-200",
};

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
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
