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
      {leads.map((lead, index) => (
        <li
          key={lead.id}
          className="motion-safe:animate-fade-in-up"
          style={{ animationDelay: `${Math.min(index, 6) * 40}ms` }}
        >
          <Link
            href={`/dashboard/campaigns/${campaignId}/leads/${lead.id}`}
            className="group block"
          >
            <Card className="transition-[box-shadow,transform,border-color] duration-200 group-hover:-translate-y-0.5 group-hover:border-indigo-200 group-hover:shadow-[var(--shadow-card-hover)] dark:group-hover:border-indigo-500/40 dark:group-hover:shadow-[var(--shadow-card-hover-dark)]">
              <CardContent className="flex items-center justify-between gap-4 py-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                    {lead.company.name}
                  </p>
                  <p className="truncate text-xs text-slate-500 dark:text-slate-400">
                    {lead.company.domain}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-4">
                  <span className="text-sm font-semibold tabular-nums text-slate-700 dark:text-slate-300">
                    {lead.score}/100
                  </span>
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
