import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { LeadStatusBadge } from "@/components/campaigns/lead-status-badge";
import type { LeadSummaryResponse } from "@/lib/types/api";

export function LeadList({
  campaignId,
  leads,
}: {
  campaignId: string;
  leads: LeadSummaryResponse[];
}) {
  return (
    <ul className="space-y-3">
      {leads.map((lead) => (
        <li key={lead.id}>
          <Link href={`/dashboard/campaigns/${campaignId}/leads/${lead.id}`}>
            <Card className="transition-colors hover:border-indigo-300">
              <CardContent className="flex items-center justify-between gap-4 p-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{lead.company.name}</p>
                  <p className="truncate text-xs text-slate-500">{lead.company.domain}</p>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <span className="text-sm font-semibold text-slate-700">{lead.score}/100</span>
                  <LeadStatusBadge status={lead.status} />
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
