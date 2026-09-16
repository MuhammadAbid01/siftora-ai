import { Skeleton } from "@/components/ui/skeleton";

export default function LeadsLoading() {
  return (
    <div role="status" aria-label="Loading leads" className="space-y-4">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-16 w-full" />
      <Skeleton className="h-16 w-full" />
    </div>
  );
}
