import type { ReactNode } from "react";
import { cn } from "@/lib/cn";

export function EmptyState({
  title,
  description,
  action,
  icon,
  size = "default",
  className,
}: {
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
  /** "lg" is for a page's single primary empty state (e.g. an all-caught-up
   * queue) — bigger icon treatment, more breathing room. */
  size?: "default" | "lg";
  className?: string;
}) {
  const large = size === "lg";
  return (
    <div
      className={cn(
        "flex flex-col items-center gap-3 rounded-xl border border-dashed border-slate-300 bg-white/60 text-center dark:border-slate-700 dark:bg-slate-900/40",
        large ? "px-6 py-16 sm:py-20" : "px-6 py-12",
        className,
      )}
    >
      {icon && (
        <div
          className={cn(
            "flex items-center justify-center rounded-full text-indigo-600 dark:text-indigo-300",
            large
              ? "size-16 bg-gradient-to-b from-indigo-50 to-indigo-100/60 ring-1 ring-indigo-100 dark:from-indigo-500/15 dark:to-indigo-500/5 dark:ring-indigo-500/20"
              : "size-11 bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500",
          )}
        >
          {icon}
        </div>
      )}
      <div className="space-y-1">
        <p
          className={cn(
            "font-medium text-slate-900 dark:text-slate-100",
            large ? "text-base" : "text-sm",
          )}
        >
          {title}
        </p>
        {description && (
          <p
            className={cn(
              "text-slate-500 dark:text-slate-400",
              large ? "mx-auto max-w-sm text-sm" : "text-sm",
            )}
          >
            {description}
          </p>
        )}
      </div>
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
