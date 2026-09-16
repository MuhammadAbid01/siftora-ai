import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { ApprovalStatus } from "@/lib/types/api";

const STATUS_LABELS: Record<ApprovalStatus, string> = {
  pending: "Pending review",
  approved: "Approved",
  rejected: "Rejected",
};

const STATUS_VARIANTS: Record<ApprovalStatus, BadgeProps["variant"]> = {
  pending: "warning",
  approved: "success",
  rejected: "neutral",
};

export function ApprovalStatusBadge({ status }: { status: ApprovalStatus }) {
  return <Badge variant={STATUS_VARIANTS[status]}>{STATUS_LABELS[status]}</Badge>;
}
