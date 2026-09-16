import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { QualityStatus } from "@/lib/types/api";

const STATUS_LABELS: Record<QualityStatus, string> = {
  passed: "Quality check passed",
  needs_review: "Needs review",
};

const STATUS_VARIANTS: Record<QualityStatus, BadgeProps["variant"]> = {
  passed: "success",
  needs_review: "danger",
};

export function QualityStatusBadge({ status }: { status: QualityStatus }) {
  return <Badge variant={STATUS_VARIANTS[status]}>{STATUS_LABELS[status]}</Badge>;
}
