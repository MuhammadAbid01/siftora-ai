import { cn } from "@/lib/cn";
import type { CampaignStatus } from "@/lib/types/api";

const STEPS = ["Brief", "Review plan", "Approve & run"] as const;

/** Maps a campaign's real lifecycle status onto the 3-step flow shown on
 * both the "New campaign" page and the campaign detail page (which acts as
 * the plan-review/approval step) — every step reflects an actual state
 * transition, not an artificial wizard step. */
function stepForStatus(status: CampaignStatus | "new"): number {
  if (status === "new" || status === "draft" || status === "awaiting_plan_approval") {
    return status === "new" ? 1 : 2;
  }
  return 3;
}

export function CampaignSteps({ status }: { status: CampaignStatus | "new" }) {
  const active = stepForStatus(status);
  return (
    <ol
      aria-label="Campaign progress"
      className="flex flex-wrap items-center gap-x-2 gap-y-1.5 text-xs font-medium"
    >
      {STEPS.map((label, index) => {
        const step = index + 1;
        const state = step < active ? "done" : step === active ? "current" : "upcoming";
        return (
          <li key={label} className="flex items-center gap-2">
            <span
              className={cn(
                "flex size-5 shrink-0 items-center justify-center rounded-full text-[11px] font-semibold",
                state === "done" && "bg-indigo-600 text-white dark:bg-indigo-500",
                state === "current" &&
                  "bg-indigo-100 text-indigo-700 ring-2 ring-indigo-500 dark:bg-indigo-500/20 dark:text-indigo-300 dark:ring-indigo-400",
                state === "upcoming" &&
                  "bg-slate-100 text-slate-400 dark:bg-slate-800 dark:text-slate-500",
              )}
            >
              {state === "done" ? (
                <svg width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path
                    d="M3 8.5 6.5 12 13 4.5"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              ) : (
                step
              )}
            </span>
            <span
              className={cn(
                state === "upcoming"
                  ? "text-slate-400 dark:text-slate-600"
                  : "text-slate-700 dark:text-slate-200",
              )}
            >
              {label}
            </span>
            {step < STEPS.length && (
              <span aria-hidden="true" className="mx-0.5 h-px w-6 bg-slate-200 dark:bg-slate-700" />
            )}
          </li>
        );
      })}
    </ol>
  );
}
