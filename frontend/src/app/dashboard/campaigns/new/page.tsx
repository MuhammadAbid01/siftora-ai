import type { Metadata } from "next";
import { NewCampaignForm } from "@/components/campaigns/new-campaign-form";

export const metadata: Metadata = {
  title: "New campaign",
};

export default function NewCampaignPage() {
  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">New campaign</h1>
        <p className="mt-1 text-sm text-slate-500">
          Describe who you&apos;re trying to reach in plain language. You&apos;ll be able to review
          and edit the generated ICP before approving it.
        </p>
      </div>
      <NewCampaignForm />
    </div>
  );
}
