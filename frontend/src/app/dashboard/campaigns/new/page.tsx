import type { Metadata } from "next";
import { NewCampaignForm } from "@/components/campaigns/new-campaign-form";
import { CampaignSteps } from "@/components/campaigns/campaign-steps";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export const metadata: Metadata = {
  title: "New campaign",
};

const TIPS = [
  "Name the industry, location, and rough company size you're targeting.",
  "Mention signals worth researching for — active hiring, a specific tech stack, recent funding.",
  "Call out anything to exclude (e.g. recruitment agencies, companies without a website).",
];

export default function NewCampaignPage() {
  return (
    <div className="max-w-4xl space-y-6 motion-safe:animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          New campaign
        </h1>
        <div className="mt-2">
          <CampaignSteps status="new" />
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <NewCampaignForm />
        </div>

        <Card className="h-fit lg:col-span-2">
          <CardHeader>
            <CardTitle>Writing a good brief</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2.5 text-sm text-slate-600 dark:text-slate-400">
              {TIPS.map((tip) => (
                <li key={tip} className="flex gap-2.5">
                  <span
                    aria-hidden="true"
                    className="mt-0.5 flex size-4 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300"
                  >
                    <svg width="9" height="9" viewBox="0 0 16 16" fill="none">
                      <path
                        d="M3 8.5 6.5 12 13 4.5"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  </span>
                  {tip}
                </li>
              ))}
            </ul>
            <div className="rounded-lg border border-dashed border-slate-200 bg-slate-50 p-3.5 text-xs text-slate-500 dark:border-slate-700 dark:bg-slate-900/60 dark:text-slate-400">
              <p className="mb-1 font-medium text-slate-700 dark:text-slate-300">Example</p>
              &ldquo;Find animation and design agencies in Dubai with 5–50 employees, an active
              website, and signs they could benefit from AI customer support.&rdquo;
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              After you submit, the agent proposes a structured ICP and search plan on the next
              screen — you review and approve it before research runs.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
