import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/campaigns/status-badge";
import type { CampaignResponse } from "@/lib/types/api";

export function CampaignList({ campaigns }: { campaigns: CampaignResponse[] }) {
  return (
    <ul className="space-y-3">
      {campaigns.map((campaign, index) => (
        <li
          key={campaign.id}
          className="motion-safe:animate-fade-in-up"
          style={{ animationDelay: `${Math.min(index, 6) * 40}ms` }}
        >
          <Link href={`/dashboard/campaigns/${campaign.id}`} className="group block">
            <Card className="transition-[box-shadow,transform,border-color] duration-200 group-hover:-translate-y-0.5 group-hover:border-indigo-200 group-hover:shadow-[var(--shadow-card-hover)] dark:group-hover:border-indigo-500/40 dark:group-hover:shadow-[var(--shadow-card-hover-dark)]">
              <CardContent className="flex items-center justify-between gap-4 py-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900 dark:text-slate-100">
                    {campaign.brief}
                  </p>
                  <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Target: {campaign.target_lead_count} leads
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <StatusBadge status={campaign.status} />
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 16 16"
                    fill="none"
                    aria-hidden="true"
                    className="text-slate-300 transition-transform group-hover:translate-x-0.5 group-hover:text-slate-400 dark:text-slate-600 dark:group-hover:text-slate-500"
                  >
                    <path
                      d="M6 3.5 10.5 8 6 12.5"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </div>
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
