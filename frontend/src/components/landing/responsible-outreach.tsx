import { Reveal } from "@/components/ui/reveal";

const PRINCIPLES = [
  "Research is limited to permitted public business information.",
  "No bypassing authentication, CAPTCHAs, access controls, or rate limits.",
  "Suppression and opt-out state is always respected.",
  "Real sending is opt-in, rate-limited, and requires explicit approval.",
];

export function ResponsibleOutreach() {
  return (
    <section
      id="responsible-use"
      className="relative overflow-hidden border-t border-slate-200 bg-indigo-950 text-indigo-50 dark:border-slate-800"
    >
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(129,140,248,0.18),transparent_55%)]"
      />
      <div className="relative mx-auto max-w-4xl px-4 py-20 sm:px-6">
        <Reveal>
          <h2 className="text-2xl font-semibold tracking-tight">Responsible by design</h2>
          <p className="mt-4 text-indigo-200">
            Siftora is built to keep a human in control of every outreach decision.
          </p>
        </Reveal>
        <Reveal delayMs={80}>
          <ul className="mt-8 space-y-3">
            {PRINCIPLES.map((principle) => (
              <li key={principle} className="flex gap-3">
                <span
                  aria-hidden="true"
                  className="mt-1 flex size-5 shrink-0 items-center justify-center rounded-full bg-indigo-800/60 text-indigo-300"
                >
                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                    <path
                      d="M3 8.5 6.5 12 13 4.5"
                      stroke="currentColor"
                      strokeWidth="1.75"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                </span>
                <span>{principle}</span>
              </li>
            ))}
          </ul>
        </Reveal>
      </div>
    </section>
  );
}
