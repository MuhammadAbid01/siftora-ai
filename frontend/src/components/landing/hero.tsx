import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export function Hero() {
  return (
    <section className="border-b border-slate-200 bg-gradient-to-b from-indigo-50 to-white">
      <div className="mx-auto max-w-4xl px-4 py-20 text-center sm:px-6 sm:py-28">
        <p className="mb-4 text-sm font-semibold uppercase tracking-wide text-indigo-600">
          Agentic Lead Intelligence Platform
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
          Siftora researches companies, verifies evidence, and drafts outreach — you approve every
          send.
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-slate-600">
          Turn an open-ended campaign goal into a qualified, evidence-backed lead list. Every claim
          traces back to a source. No action reaches a prospect without your sign-off.
        </p>
        <div className="mt-10 flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Link href="/sign-up" className={cn(buttonVariants({ size: "lg" }))}>
            Start Campaign
          </Link>
          <a href="#demo" className={cn(buttonVariants({ variant: "secondary", size: "lg" }))}>
            View Demo
          </a>
        </div>
      </div>
    </section>
  );
}
