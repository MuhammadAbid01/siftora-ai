import type { ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/cn";

const alertVariants = cva("rounded-xl border p-4 text-sm motion-safe:animate-fade-in", {
  variants: {
    variant: {
      error:
        "border-red-200 bg-red-50 text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-300",
      warning:
        "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-300",
      info: "border-sky-200 bg-sky-50 text-sky-800 dark:border-sky-500/30 dark:bg-sky-500/10 dark:text-sky-300",
      success:
        "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-300",
    },
  },
  defaultVariants: {
    variant: "error",
  },
});

const ICON_TONE: Record<NonNullable<VariantProps<typeof alertVariants>["variant"]>, string> = {
  error: "bg-red-100 text-red-600 dark:bg-red-500/15 dark:text-red-300",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300",
  info: "bg-sky-100 text-sky-700 dark:bg-sky-500/15 dark:text-sky-300",
  success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300",
};

export interface AlertProps extends VariantProps<typeof alertVariants> {
  children: ReactNode;
  className?: string;
  /** Optional heading rendered above the body — turns the alert into a
   * fuller banner treatment (icon + title + body) for prominent notices. */
  title?: string;
  /** Optional leading icon (18x18 viewBox recommended). */
  icon?: ReactNode;
}

/** A single unified banner for error/warning/info/success messaging — used
 * in place of the ad-hoc `role="alert"` red boxes previously duplicated
 * across every page. Pass `title`/`icon` for a fuller banner treatment.
 */
export function Alert({ variant = "error", children, className, title, icon }: AlertProps) {
  if (!title && !icon) {
    return (
      <div role="alert" className={cn(alertVariants({ variant }), className)}>
        {children}
      </div>
    );
  }

  return (
    <div role="alert" className={cn(alertVariants({ variant }), "flex gap-3", className)}>
      {icon && (
        <div
          aria-hidden="true"
          className={cn(
            "flex size-8 shrink-0 items-center justify-center rounded-lg",
            ICON_TONE[variant ?? "error"],
          )}
        >
          {icon}
        </div>
      )}
      <div className="space-y-1">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? "text-current/90" : undefined}>{children}</div>
      </div>
    </div>
  );
}
