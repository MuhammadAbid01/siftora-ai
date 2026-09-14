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
    <section id="workflow" className="border-t border-slate-200 bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
        <h2 className="text-2xl font-semibold text-slate-900">How Siftora works</h2>
        <div className="mt-10 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, index) => (
            <div key={step.title}>
              <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white">
                {index + 1}
              </div>
              <h3 className="text-base font-semibold text-slate-900">{step.title}</h3>
              <p className="mt-2 text-sm text-slate-600">{step.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
