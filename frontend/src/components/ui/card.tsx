"use client";

import * as React from "react";
import { cn } from "@/lib/cn";
import { useDensity } from "@/lib/density/density-provider";

export function Card({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "rounded-xl border border-slate-200 bg-white shadow-[var(--shadow-card)] transition-[box-shadow,border-color,transform] duration-200 ease-out motion-reduce:transition-none dark:border-slate-800 dark:bg-slate-900 dark:shadow-[var(--shadow-card-dark)]",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const { density } = useDensity();
  return (
    <div
      className={cn("flex flex-col gap-1.5", density === "compact" ? "p-4" : "p-6", className)}
      {...props}
    />
  );
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={cn(
        "text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100",
        className,
      )}
      {...props}
    />
  );
}

export function CardDescription({
  className,
  ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("text-sm text-slate-500 dark:text-slate-400", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const { density } = useDensity();
  return (
    <div className={cn(density === "compact" ? "p-4 pt-0" : "p-6 pt-0", className)} {...props} />
  );
}
