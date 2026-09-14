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
      className="border-t border-slate-200 bg-indigo-950 text-indigo-50"
    >
      <div className="mx-auto max-w-4xl px-4 py-20 sm:px-6">
        <h2 className="text-2xl font-semibold">Responsible by design</h2>
        <p className="mt-4 text-indigo-200">
          Siftora is built to keep a human in control of every outreach decision.
        </p>
        <ul className="mt-8 space-y-3">
          {PRINCIPLES.map((principle) => (
            <li key={principle} className="flex gap-3">
              <span aria-hidden="true" className="mt-1 text-indigo-300">
                &#8226;
              </span>
              <span>{principle}</span>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
