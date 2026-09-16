import { Reveal } from "@/components/ui/reveal";

const STACK = [
  "Next.js + TypeScript",
  "Tailwind CSS",
  "FastAPI + Python",
  "Pydantic",
  "Supabase (Postgres + Auth)",
  "LangGraph",
];

export function TechStack() {
  return (
    <section id="technology" className="mx-auto max-w-4xl px-4 py-20 sm:px-6">
      <Reveal>
        <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
          Technology
        </h2>
        <div className="mt-6 flex flex-wrap gap-3">
          {STACK.map((item) => (
            <span
              key={item}
              className="rounded-full border border-slate-200 bg-white px-4 py-1.5 text-sm text-slate-700 shadow-xs transition-colors hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-indigo-500/30 dark:hover:bg-indigo-500/10 dark:hover:text-indigo-300"
            >
              {item}
            </span>
          ))}
        </div>
      </Reveal>
    </section>
  );
}
