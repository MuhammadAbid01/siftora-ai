import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Reveal } from "@/components/ui/reveal";

const DEMO_ROWS = [
  { company: "Northbeam Studio", score: 88, status: "Qualified", variant: "success" as const },
  { company: "Vantage Motion Co.", score: 71, status: "Needs review", variant: "warning" as const },
  { company: "Pixel & Pine", score: 42, status: "Rejected", variant: "neutral" as const },
];

export function ProductMockup() {
  return (
    <section id="demo" className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
      <Reveal>
        <div className="mb-8 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
            See it in action
          </h2>
          <Badge variant="info">Demo data</Badge>
        </div>
        <Card>
          <CardHeader>
            <CardTitle>Campaign: Animation &amp; design agencies — Dubai</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-4 text-sm text-slate-500 dark:text-slate-400">
              This table uses labeled demo data to illustrate the product — it is not a live
              campaign result.
            </p>
            <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-slate-500 dark:bg-slate-900 dark:text-slate-400">
                  <tr>
                    <th className="px-4 py-2.5 font-medium">Company</th>
                    <th className="px-4 py-2.5 font-medium">Score</th>
                    <th className="px-4 py-2.5 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {DEMO_ROWS.map((row) => (
                    <tr
                      key={row.company}
                      className="transition-colors hover:bg-slate-50/80 dark:hover:bg-slate-800/60"
                    >
                      <td className="px-4 py-3 font-medium text-slate-900 dark:text-slate-100">
                        {row.company}
                      </td>
                      <td className="px-4 py-3 text-slate-700 tabular-nums dark:text-slate-300">
                        {row.score}/100
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={row.variant}>{row.status}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </Reveal>
    </section>
  );
}
