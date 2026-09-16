import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { LeadStatus } from "@/lib/types/api";

const STATUS_LABELS: Record<LeadStatus, string> = {
  qualified: "Qualified",
  needs_review: "Needs review",
  rejected: "Rejected",
};

const STATUS_VARIANTS: Record<LeadStatus, BadgeProps["variant"]> = {
  qualified: "success",
  needs_review: "warning",
  rejected: "neutral",
};

export function LeadStatusBadge({ status }: { status: LeadStatus }) {
  return <Badge variant={STATUS_VARIANTS[status]}>{STATUS_LABELS[status]}</Badge>;
}
