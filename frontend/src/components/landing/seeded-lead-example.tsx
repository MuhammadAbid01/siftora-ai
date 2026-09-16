import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";

const EVIDENCE = [
  {
    type: "Fact",
    variant: "success" as const,
    claim: "“Northbeam Studio lists 22 employees and an active portfolio of animation clients.”",
    meta: "Source: northbeamstudio.example/about — retrieved as demo fixture",
  },
  {
    type: "Inference",
    variant: "brand" as const,
    claim:
      "“Growing client roster suggests capacity constraints that manual workflows may struggle to meet.”",
  },
  {
    type: "Unknown",
    variant: "neutral" as const,
    claim: "“No public signal found on current customer support tooling.”",
  },
];

export function SeededLeadExample() {
  return (
    <section className="mx-auto max-w-4xl px-4 py-20 sm:px-6">
      <Reveal>
        <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            Evidence in practice
          </h2>
          <Badge variant="info">Demo data</Badge>
        </div>
        <Card>
          <CardHeader>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <CardTitle>Northbeam Studio</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                  88/100
                </span>
                <Badge variant="success">Qualified</Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {EVIDENCE.map((item) => (
              <div
                key={item.type}
                className="border-l-2 border-slate-100 pl-4 dark:border-slate-800"
              >
                <Badge variant={item.variant} className="mb-1.5">
                  {item.type}
                </Badge>
                <p className="text-slate-600 dark:text-slate-400">{item.claim}</p>
                {item.meta && (
                  <p className="mt-1 text-xs text-slate-400 dark:text-slate-500">{item.meta}</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </Reveal>
    </section>
  );
}
