import { Reveal } from "@/components/ui/reveal";

const BEHAVIORS = [
  "Interprets an open-ended campaign goal instead of following a fixed script.",
  "Revises weak search queries within fixed limits, rather than giving up.",
  "Rejects irrelevant, duplicate, or unsupported candidates instead of accepting everything.",
  "Pauses before external actions and waits for human approval.",
  "Recovers from tool failures without inventing results.",
];

export function WhyAgentic() {
  return (
    <section className="mx-auto max-w-4xl px-4 py-20 sm:px-6">
      <Reveal>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Why this is agentic, not a fixed pipeline
        </h2>
        <p className="mt-4 text-slate-600 dark:text-slate-400">
          Siftora is not a single LLM prompt or a fixed sequence of steps. Deterministic application
          code enforces scoring, limits, and approvals — the agent decides how to research and when
          to stop trying.
        </p>
      </Reveal>
      <Reveal>
        <ul className="mt-8 space-y-3">
          {BEHAVIORS.map((behavior, index) => (
            <li
              key={behavior}
              className="flex gap-3 text-slate-700 motion-safe:animate-fade-in-up dark:text-slate-300"
              style={{ animationDelay: `${index * 60}ms` }}
            >
              <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  <path
                    d="M3 8.5 6.5 12 13 4.5"
                    stroke="currentColor"
                    strokeWidth="1.75"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </span>
              <span>{behavior}</span>
            </li>
          ))}
        </ul>
      </Reveal>
    </section>
  );
}
