const STACK = [
  "Next.js + TypeScript",
  "Tailwind CSS",
  "FastAPI + Python",
  "Pydantic",
  "Supabase (Postgres + Auth)",
  "LangGraph (Phase 3+)",
];

export function TechStack() {
  return (
    <section id="technology" className="mx-auto max-w-4xl px-4 py-20 sm:px-6">
      <h2 className="text-2xl font-semibold text-slate-900">Technology</h2>
      <div className="mt-6 flex flex-wrap gap-3">
        {STACK.map((item) => (
          <span
            key={item}
            className="rounded-full border border-slate-200 bg-white px-4 py-1.5 text-sm text-slate-700"
          >
            {item}
          </span>
        ))}
      </div>
    </section>
  );
}
