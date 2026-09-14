export default function CampaignDetailLoading() {
  return (
    <div role="status" aria-label="Loading campaign" className="space-y-4">
      <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
      <div className="h-40 w-full animate-pulse rounded-lg bg-slate-200" />
      <div className="h-40 w-full animate-pulse rounded-lg bg-slate-200" />
    </div>
  );
}
