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
      <h2 className="text-2xl font-semibold text-slate-900">
        Why this is agentic, not a fixed pipeline
      </h2>
      <p className="mt-4 text-slate-600">
        Siftora is not a single LLM prompt or a fixed sequence of steps. Deterministic application
        code enforces scoring, limits, and approvals — the agent decides how to research and when to
        stop trying.
      </p>
      <ul className="mt-8 space-y-3">
        {BEHAVIORS.map((behavior) => (
          <li key={behavior} className="flex gap-3 text-slate-700">
            <span aria-hidden="true" className="mt-1 text-indigo-600">
              &#8226;
            </span>
            <span>{behavior}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
