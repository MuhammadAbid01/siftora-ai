import { Reveal } from "@/components/ui/reveal";

// Generic placeholder wordmarks — no real company names/logos, per the
// project's honesty rule against implying real customers before there are
// any (see plan.md §14: "No fake logos, testimonials, revenue metrics").
const PLACEHOLDER_MARKS = ["Northwind", "Brightpath", "Cascade", "Meridian", "Alderfield", "Varro"];

export function LogoStrip() {
  return (
    <section className="border-t border-slate-200 bg-white py-12 dark:border-slate-800 dark:bg-slate-950">
      <div className="mx-auto max-w-5xl px-4 sm:px-6">
        <Reveal>
          <p className="text-center text-xs font-semibold tracking-wide text-slate-500 uppercase dark:text-slate-500">
            Built for teams that need evidence-backed outreach
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-10 gap-y-4 grayscale">
            {PLACEHOLDER_MARKS.map((mark) => (
              <span
                key={mark}
                className="text-lg font-semibold tracking-tight text-slate-300 select-none dark:text-slate-700"
              >
                {mark}
              </span>
            ))}
          </div>
          <p className="mt-3 text-center text-[11px] text-slate-400 dark:text-slate-600">
            Illustrative placeholder marks — not real customers.
          </p>
        </Reveal>
      </div>
    </section>
  );
}
