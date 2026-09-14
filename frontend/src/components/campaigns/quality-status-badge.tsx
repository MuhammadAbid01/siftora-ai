import { cn } from "@/lib/cn";
import type { QualityStatus } from "@/lib/types/api";

const STATUS_LABELS: Record<QualityStatus, string> = {
  passed: "Quality check passed",
  needs_review: "Needs review",
};

const STATUS_STYLES: Record<QualityStatus, string> = {
  passed: "bg-emerald-50 text-emerald-700 border-emerald-200",
  needs_review: "bg-red-50 text-red-700 border-red-200",
};

export function QualityStatusBadge({ status }: { status: QualityStatus }) {
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
