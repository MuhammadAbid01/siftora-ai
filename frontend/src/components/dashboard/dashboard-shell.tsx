"use client";

import type { ReactNode } from "react";
import { DashboardNav } from "@/components/dashboard/dashboard-nav";
import { Topbar } from "@/components/dashboard/topbar";
import { useSidebar } from "@/components/dashboard/sidebar-context";
import { cn } from "@/lib/cn";

/** Wraps the sidebar + topbar + content area so the content's left padding
 * can follow the desktop sidebar's collapsed/expanded width — the sidebar
 * and this padding live in different components with no parent/child
 * relationship, so both read the same `SidebarProvider` state. */
export function DashboardShell({ email, children }: { email: string; children: ReactNode }) {
  const { collapsed } = useSidebar();

  return (
    <div className="min-h-full bg-slate-50 dark:bg-slate-950">
      <DashboardNav />
      <div
        className={cn(
          "flex min-h-full flex-col transition-[padding] duration-200 ease-out motion-reduce:transition-none",
          collapsed ? "md:pl-[72px]" : "md:pl-64",
        )}
      >
        <Topbar email={email} />
        <main className="flex-1">
          <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-6 lg:py-10">{children}</div>
        </main>
      </div>
    </div>
  );
}
