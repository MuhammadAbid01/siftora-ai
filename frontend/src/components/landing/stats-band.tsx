import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";

// Illustrative figures for a fixture/demo-mode run — explicitly labeled as
// such (same honesty convention as ProductMockup/SeededLeadExample's "Demo
// data" badge), not presented as live usage metrics. See plan.md §14.
const STATS = [
  { value: "5–10", label: "Companies researched per demo run" },
  { value: "100%", label: "Facts require a source URL" },
  { value: "0", label: "Sends without human approval" },
  { value: "8", label: "Weighted scoring criteria" },
];

export function StatsBand() {
  return (
    <section className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/40">
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <Reveal>
          <div className="mb-8 flex flex-wrap items-center justify-center gap-3 text-center sm:justify-between">
            <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
              What the numbers mean here
            </h2>
            <Badge variant="info">Demo metrics</Badge>
          </div>
        </Reveal>
        <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
          {STATS.map((stat, index) => (
            <Reveal key={stat.label} delayMs={index * 70} className="text-center">
              <p className="text-3xl font-bold tracking-tight text-indigo-600 tabular-nums sm:text-4xl dark:text-indigo-400">
                {stat.value}
              </p>
              <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-400">{stat.label}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
