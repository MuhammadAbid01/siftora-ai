import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { StatusBadge } from "@/components/campaigns/status-badge";
import type { CampaignResponse } from "@/lib/types/api";

export function CampaignList({ campaigns }: { campaigns: CampaignResponse[] }) {
  return (
    <ul className="space-y-3">
      {campaigns.map((campaign) => (
        <li key={campaign.id}>
          <Link href={`/dashboard/campaigns/${campaign.id}`}>
            <Card className="transition-colors hover:border-indigo-300">
              <CardContent className="flex items-center justify-between p-4">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">{campaign.brief}</p>
                  <p className="mt-1 text-xs text-slate-500">
                    Target: {campaign.target_lead_count} leads
                  </p>
                </div>
                <StatusBadge status={campaign.status} />
              </CardContent>
            </Card>
          </Link>
        </li>
      ))}
    </ul>
  );
}
