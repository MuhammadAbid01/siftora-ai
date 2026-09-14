export default function DashboardLoading() {
  return (
    <div role="status" aria-label="Loading dashboard" className="space-y-4">
      <div className="h-8 w-48 animate-pulse rounded bg-slate-200" />
      <div className="h-40 w-full animate-pulse rounded-lg bg-slate-200" />
    </div>
  );
}
