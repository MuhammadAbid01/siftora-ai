import Link from "next/link";
import type { ReactNode } from "react";

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="relative flex min-h-full flex-1 flex-col items-center justify-center overflow-hidden bg-slate-50 px-4 py-16 dark:bg-slate-950">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.12),transparent_55%)] dark:bg-[radial-gradient(circle_at_50%_0%,rgba(99,102,241,0.15),transparent_55%)]"
      />
      <Link
        href="/"
        className="relative z-10 mb-8 flex items-center gap-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100"
      >
        <span className="flex size-7 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white dark:bg-indigo-500">
          S
        </span>
        Siftora
      </Link>
      <div className="relative z-10 w-full max-w-sm rounded-2xl border border-slate-200 bg-white p-8 shadow-[var(--shadow-card-hover)] motion-safe:animate-scale-in dark:border-slate-800 dark:bg-slate-900 dark:shadow-[var(--shadow-card-hover-dark)]">
        {children}
      </div>
    </div>
  );
}
