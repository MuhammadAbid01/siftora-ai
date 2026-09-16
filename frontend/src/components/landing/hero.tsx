import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";
import { cn } from "@/lib/cn";

const TRUST_PILLS = ["Evidence-backed", "Deterministic scoring", "Human-approved"];

const PREVIEW_ROWS = [
  { company: "Northbeam Studio", score: 88, variant: "success" as const },
  { company: "Vantage Motion Co.", score: 71, variant: "warning" as const },
];

export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-950">
      {/* Decorative background: a soft radial glow plus a faint dot grid —
          purely presentational (aria-hidden), no layout impact. */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0">
        <div className="absolute left-1/2 top-[-12rem] h-[36rem] w-[64rem] -translate-x-1/2 rounded-full bg-gradient-to-b from-indigo-100 via-indigo-50 to-transparent blur-3xl dark:from-indigo-500/20 dark:via-indigo-500/5 dark:to-transparent" />
        <div
          className="absolute inset-0 opacity-[0.35] dark:opacity-[0.15]"
          style={{
            backgroundImage: "radial-gradient(circle, rgba(99,102,241,0.15) 1px, transparent 1px)",
            backgroundSize: "24px 24px",
            maskImage: "linear-gradient(to bottom, black, transparent 70%)",
          }}
        />
      </div>

      <div className="relative mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-28">
        <div className="motion-safe:animate-fade-in-up">
          <p className="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-200 bg-indigo-50 px-3.5 py-1 text-xs font-semibold tracking-wide text-indigo-700 uppercase dark:border-indigo-500/30 dark:bg-indigo-500/10 dark:text-indigo-300">
            <span className="size-1.5 rounded-full bg-indigo-500 motion-safe:animate-pulse" />
            Agentic Lead Intelligence Platform
          </p>
          <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight text-balance text-slate-900 sm:text-5xl sm:leading-[1.1] lg:text-6xl dark:text-slate-100">
            Siftora researches companies, verifies evidence, and drafts outreach —{" "}
            <span className="bg-gradient-to-r from-indigo-600 to-violet-600 bg-clip-text text-transparent dark:from-indigo-400 dark:to-violet-400">
              you approve every send.
            </span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-balance text-slate-600 dark:text-slate-400">
            Turn an open-ended campaign goal into a qualified, evidence-backed lead list. Every
            claim traces back to a source. No action reaches a prospect without your sign-off.
          </p>
        </div>

        <div
          className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row motion-safe:animate-fade-in-up"
          style={{ animationDelay: "100ms" }}
        >
          <Link
            href="/sign-up"
            className={cn(buttonVariants({ size: "lg" }), "group w-full sm:w-auto")}
          >
            Start Campaign
            <svg
              width="16"
              height="16"
              viewBox="0 0 16 16"
              fill="none"
              aria-hidden="true"
              className="transition-transform duration-150 motion-reduce:transition-none group-hover:translate-x-0.5"
            >
              <path
                d="M3.5 8h9m0 0-4-4m4 4-4 4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </Link>
          <a
            href="#demo"
            className={cn(buttonVariants({ variant: "secondary", size: "lg" }), "w-full sm:w-auto")}
          >
            View Demo
          </a>
        </div>

        <div
          className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 motion-safe:animate-fade-in-up"
          style={{ animationDelay: "180ms" }}
        >
          {TRUST_PILLS.map((pill) => (
            <span
              key={pill}
              className="flex items-center gap-1.5 text-sm text-slate-500 dark:text-slate-400"
            >
              <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                <path
                  d="M3 8.5 6.5 12 13 4.5"
                  className="stroke-indigo-600 dark:stroke-indigo-400"
                  strokeWidth="1.75"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
              {pill}
            </span>
          ))}
        </div>

        <Reveal delayMs={220} className="mt-14">
          <div
            aria-hidden="true"
            className="mx-auto max-w-lg motion-safe:animate-float motion-safe:[animation-delay:0.6s]"
          >
            <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white/80 text-left shadow-2xl shadow-indigo-900/10 backdrop-blur-md dark:border-slate-800/80 dark:bg-slate-900/80 dark:shadow-black/40">
              <div className="flex items-center gap-1.5 border-b border-slate-100 px-4 py-3 dark:border-slate-800">
                <span className="size-2.5 rounded-full bg-red-300 dark:bg-red-500/50" />
                <span className="size-2.5 rounded-full bg-amber-300 dark:bg-amber-500/50" />
                <span className="size-2.5 rounded-full bg-emerald-300 dark:bg-emerald-500/50" />
                <span className="ml-3 text-xs font-medium text-slate-400 dark:text-slate-500">
                  Campaign: Dubai design agencies
                </span>
              </div>
              <div className="space-y-2.5 p-4">
                {PREVIEW_ROWS.map((row) => (
                  <div
                    key={row.company}
                    className="flex items-center justify-between rounded-lg bg-slate-50 px-3 py-2.5 dark:bg-slate-800/60"
                  >
                    <span className="text-sm font-medium text-slate-800 dark:text-slate-200">
                      {row.company}
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 tabular-nums dark:text-slate-400">
                        {row.score}/100
                      </span>
                      <Badge variant={row.variant}>
                        {row.variant === "success" ? "Qualified" : "Needs review"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  );
}
