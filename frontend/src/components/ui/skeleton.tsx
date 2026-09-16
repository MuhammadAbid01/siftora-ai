import { cn } from "@/lib/cn";

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "motion-safe:animate-pulse rounded-md bg-slate-200/80 dark:bg-slate-800/80",
        className,
      )}
      {...props}
    />
  );
}
