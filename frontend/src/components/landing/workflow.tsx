import { Reveal } from "@/components/ui/reveal";

const STEPS = [
  {
    title: "Define ICP",
    description:
      "Describe your ideal customer in plain language; Siftora structures it into a reviewable profile.",
  },
  {
    title: "Research",
    description:
      "The agent searches, visits public websites, and extracts facts with a source for each claim.",
  },
  {
    title: "Verify & score",
    description:
      "Candidates are validated, deduplicated, and given a deterministic, explainable 0–100 score.",
  },
  {
    title: "Approve",
    description:
      "You review evidence and drafts, then approve, edit, reject, or regenerate before anything goes out.",
  },
];

export function Workflow() {
  return (
    <section
      id="workflow"
      className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"
    >
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
        <Reveal>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            How Siftora works
          </h2>
        </Reveal>
        <div className="relative mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
          {/* Connecting line behind the numbered dots on large screens. */}
          <div
            aria-hidden="true"
            className="absolute top-5 right-0 left-0 hidden h-px bg-slate-200 lg:block dark:bg-slate-800"
          />
          {STEPS.map((step, index) => (
            <Reveal key={step.title} delayMs={index * 80} className="relative">
              <div className="relative z-10 mb-4 flex h-10 w-10 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white shadow-[var(--shadow-glow)] dark:bg-indigo-500">
                {index + 1}
              </div>
              <h3 className="text-base font-semibold text-slate-900 dark:text-slate-100">
                {step.title}
              </h3>
              <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">{step.description}</p>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
