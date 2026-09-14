import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function SeededLeadExample() {
  return (
    <section className="mx-auto max-w-4xl px-4 py-20 sm:px-6">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-2xl font-semibold text-slate-900">Evidence in practice</h2>
        <Badge>Demo data</Badge>
      </div>
      <Card>
        <CardHeader>
          <CardTitle>Northbeam Studio — Score 88/100 (Qualified)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm">
          <div>
            <p className="font-medium text-slate-900">Fact</p>
            <p className="text-slate-600">
              &ldquo;Northbeam Studio lists 22 employees and an active portfolio of animation
              clients.&rdquo;
            </p>
            <p className="mt-1 text-xs text-slate-400">
              Source: northbeamstudio.example/about — retrieved as demo fixture
            </p>
          </div>
          <div>
            <p className="font-medium text-slate-900">Inference</p>
            <p className="text-slate-600">
              &ldquo;Growing client roster suggests capacity constraints that manual workflows may
              struggle to meet.&rdquo;
            </p>
          </div>
          <div>
            <p className="font-medium text-slate-900">Unknown</p>
            <p className="text-slate-600">
              &ldquo;No public signal found on current customer support tooling.&rdquo;
            </p>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
