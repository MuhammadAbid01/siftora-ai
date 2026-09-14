import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const DEMO_ROWS = [
  { company: "Northbeam Studio", score: 88, status: "Qualified" },
  { company: "Vantage Motion Co.", score: 71, status: "Needs review" },
  { company: "Pixel & Pine", score: 42, status: "Rejected" },
];

export function ProductMockup() {
  return (
    <section id="demo" className="mx-auto max-w-5xl px-4 py-20 sm:px-6">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-slate-900">See it in action</h2>
        <Badge>Demo data</Badge>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Campaign: Animation &amp; design agencies — Dubai</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="mb-4 text-sm text-slate-500">
            This table uses labeled demo data to illustrate the product — it is not a live campaign
            result.
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-slate-500">
                <tr>
                  <th className="px-4 py-2 font-medium">Company</th>
                  <th className="px-4 py-2 font-medium">Score</th>
                  <th className="px-4 py-2 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {DEMO_ROWS.map((row) => (
                  <tr key={row.company} className="border-t border-slate-200">
                    <td className="px-4 py-3 text-slate-900">{row.company}</td>
                    <td className="px-4 py-3 text-slate-700">{row.score}/100</td>
                    <td className="px-4 py-3 text-slate-700">{row.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
