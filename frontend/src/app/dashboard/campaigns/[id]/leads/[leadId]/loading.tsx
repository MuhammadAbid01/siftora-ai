export default function LeadDetailLoading() {
  return (
    <div role="status" aria-label="Loading lead" className="space-y-4">
      <div className="h-8 w-64 animate-pulse rounded bg-slate-200" />
      <div className="h-32 w-full animate-pulse rounded-lg bg-slate-200" />
      <div className="h-32 w-full animate-pulse rounded-lg bg-slate-200" />
    </div>
  );
}
