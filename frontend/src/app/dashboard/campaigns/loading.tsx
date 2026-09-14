export default function CampaignsLoading() {
  return (
    <div role="status" aria-label="Loading campaigns" className="space-y-4">
      <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
      <div className="h-16 w-full animate-pulse rounded-lg bg-slate-200" />
      <div className="h-16 w-full animate-pulse rounded-lg bg-slate-200" />
    </div>
  );
}
