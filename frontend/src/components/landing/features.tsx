import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";

const FEATURES = [
  {
    title: "Evidence-backed facts",
    description:
      "Every important claim links to a source URL and a stored excerpt — never invented.",
    icon: (
      <path
        d="M4 3.5h8l3 3V16a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Deterministic scoring",
    description:
      "The same inputs always produce the same 0–100 score, with a criterion-level breakdown.",
    icon: (
      <path
        d="M3 15V9m5 6V5m5 10v-4m5 4V8"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    ),
  },
  {
    title: "Human approval gate",
    description: "Drafts wait in an approval queue. The AI cannot approve its own outreach.",
    icon: (
      <path
        d="M4 9.5 8 13l8-8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
  {
    title: "Full audit trail",
    description:
      "Tool calls, agent decisions, costs, and failures are all visible on the campaign timeline.",
    icon: (
      <path
        d="M10 5.5V10l3 2M17 10a7 7 0 1 1-7-7"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    ),
  },
];

export function Features() {
  return (
    <section
      id="features"
      className="border-t border-slate-200 bg-slate-50 dark:border-slate-800 dark:bg-slate-950"
    >
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
        <Reveal>
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Built for accountable outreach
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {FEATURES.map((feature, index) => (
            <Reveal key={feature.title} delayMs={index * 70}>
              <Card className="h-full transition-[box-shadow,transform] duration-200 hover:-translate-y-0.5 hover:shadow-[var(--shadow-card-hover)] dark:hover:shadow-[var(--shadow-card-hover-dark)]">
                <CardHeader>
                  <div className="mb-1 flex size-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                      {feature.icon}
                    </svg>
                  </div>
                  <CardTitle>{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-slate-600 dark:text-slate-400">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}
