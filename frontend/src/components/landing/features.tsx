import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const FEATURES = [
  {
    title: "Evidence-backed facts",
    description:
      "Every important claim links to a source URL and a stored excerpt — never invented.",
  },
  {
    title: "Deterministic scoring",
    description:
      "The same inputs always produce the same 0–100 score, with a criterion-level breakdown.",
  },
  {
    title: "Human approval gate",
    description: "Drafts wait in an approval queue. The AI cannot approve its own outreach.",
  },
  {
    title: "Full audit trail",
    description:
      "Tool calls, agent decisions, costs, and failures are all visible on the campaign timeline.",
  },
];

export function Features() {
  return (
    <section id="features" className="border-t border-slate-200 bg-slate-50">
      <div className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
        <h2 className="text-2xl font-semibold text-slate-900">Built for accountable outreach</h2>
        <div className="mt-10 grid gap-6 sm:grid-cols-2">
          {FEATURES.map((feature) => (
            <Card key={feature.title}>
              <CardHeader>
                <CardTitle>{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-slate-600">{feature.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
