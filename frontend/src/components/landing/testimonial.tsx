import { Badge } from "@/components/ui/badge";
import { Reveal } from "@/components/ui/reveal";

export function Testimonial() {
  return (
    <section className="mx-auto max-w-3xl px-4 py-20 sm:px-6">
      <Reveal>
        <figure className="relative rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-[var(--shadow-card)] sm:p-10 dark:border-slate-800 dark:bg-slate-900 dark:shadow-[var(--shadow-card-dark)]">
          <svg
            width="32"
            height="32"
            viewBox="0 0 32 32"
            fill="none"
            aria-hidden="true"
            className="mx-auto mb-5 text-indigo-200 dark:text-indigo-500/30"
          >
            <path
              d="M9.5 8C6 8 3 11 3 15.5S6 23 9.5 23c1.5 0 2.5-1 2.5-2.5S11 18 9.5 18c-.5 0-1 .1-1.4.3.3-2.8 2.4-5 5.4-5.5V8Zm14 0c-3.5 0-6.5 3-6.5 7.5S20 23 23.5 23c1.5 0 2.5-1 2.5-2.5S25 18 23.5 18c-.5 0-1 .1-1.4.3.3-2.8 2.4-5 5.4-5.5V8Z"
              fill="currentColor"
            />
          </svg>
          <blockquote className="text-lg font-medium text-balance text-slate-800 sm:text-xl dark:text-slate-200">
            &ldquo;What sold us wasn&apos;t the automation — it was that every claim had a source we
            could click through and check before anything went to a prospect.&rdquo;
          </blockquote>
          <figcaption className="mt-6 flex items-center justify-center gap-3">
            <span className="flex size-10 items-center justify-center rounded-full bg-indigo-600 text-sm font-semibold text-white dark:bg-indigo-500">
              JR
            </span>
            <span className="text-left text-sm">
              <span className="block font-medium text-slate-900 dark:text-slate-100">
                Jordan Reyes
              </span>
              <span className="block text-slate-500 dark:text-slate-400">
                Founder, illustrative outbound agency
              </span>
            </span>
          </figcaption>
          <Badge variant="info" className="absolute top-5 right-5">
            Illustrative example
          </Badge>
        </figure>
      </Reveal>
    </section>
  );
}
