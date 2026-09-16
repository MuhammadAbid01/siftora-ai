"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";

const FOOTER_COLUMNS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: "Product",
    links: [
      { label: "How it works", href: "/#workflow" },
      { label: "Features", href: "/#features" },
      { label: "Responsible use", href: "/#responsible-use" },
    ],
  },
  {
    title: "Resources",
    links: [
      { label: "Technology", href: "/#technology" },
      { label: "GitHub", href: "https://github.com" },
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Privacy", href: "/privacy" },
      { label: "Terms", href: "/terms" },
    ],
  },
];

const SOCIAL_LINKS = [
  {
    label: "GitHub",
    href: "https://github.com",
    icon: (
      <path
        d="M8 1a7 7 0 0 0-2.2 13.64c.35.07.48-.15.48-.34v-1.2c-1.95.42-2.36-.94-2.36-.94-.32-.8-.78-1.02-.78-1.02-.64-.44.05-.43.05-.43.7.05 1.07.72 1.07.72.62 1.07 1.64.76 2.04.58.06-.45.24-.76.44-.94-1.56-.18-3.2-.78-3.2-3.48 0-.77.27-1.4.72-1.9-.07-.18-.31-.9.07-1.87 0 0 .59-.19 1.94.72a6.7 6.7 0 0 1 3.52 0c1.35-.91 1.94-.72 1.94-.72.38.97.14 1.69.07 1.87.45.5.72 1.13.72 1.9 0 2.71-1.64 3.3-3.21 3.48.25.22.48.64.48 1.3v1.92c0 .19.13.41.49.34A7 7 0 0 0 8 1Z"
        fill="currentColor"
      />
    ),
  },
  {
    label: "X",
    href: "https://x.com",
    icon: (
      <path
        d="M1.5 1.5h3.8l3 4.1 3.4-4.1h1.8L9 7.1l4.9 7.4h-3.8L6.8 10 3 14.5H1.2l5-6.1L1.5 1.5Z"
        fill="currentColor"
      />
    ),
  },
  {
    label: "LinkedIn",
    href: "https://linkedin.com",
    icon: (
      <path
        d="M3.5 5.5h-2v9h2v-9Zm-1-3.5a1.15 1.15 0 1 0 0 2.3 1.15 1.15 0 0 0 0-2.3ZM6 5.5h1.9v1.23h.03c.27-.5.9-1.03 1.87-1.03 2 0 2.37 1.32 2.37 3.03v4.77H10.2v-4.23c0-1.01-.02-2.3-1.4-2.3-1.4 0-1.62 1.1-1.62 2.23v4.3H6v-9Z"
        fill="currentColor"
      />
    ),
  },
];

function NewsletterForm() {
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <p className="text-sm text-emerald-600 dark:text-emerald-400">
        Thanks — this is a portfolio demo, so nothing was actually sent.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2 sm:flex-row">
      <label htmlFor="footer-newsletter" className="sr-only">
        Email address
      </label>
      <Input
        id="footer-newsletter"
        type="email"
        required
        placeholder="you@company.com"
        className="sm:max-w-56"
      />
      <button type="submit" className={cn(buttonVariants({ variant: "secondary", size: "md" }))}>
        Notify me
      </button>
    </form>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-gradient-to-b from-white to-slate-50 dark:border-slate-800 dark:from-slate-950 dark:to-slate-900">
      <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6">
        <div className="flex flex-col items-center gap-6 text-center">
          <h2 className="text-2xl font-semibold tracking-tight text-balance text-slate-900 dark:text-slate-100">
            Ready to see Siftora in action?
          </h2>
          <Link href="/sign-up" className={cn(buttonVariants({ size: "lg" }))}>
            Start Campaign
          </Link>
        </div>

        <div className="mt-16 grid gap-10 border-t border-slate-200 pt-12 sm:grid-cols-2 lg:grid-cols-5 dark:border-slate-800">
          <div className="lg:col-span-2">
            <Link
              href="/"
              className="flex items-center gap-2 text-lg font-semibold tracking-tight text-slate-900 dark:text-slate-100"
            >
              <span className="flex size-7 items-center justify-center rounded-lg bg-indigo-600 text-sm font-bold text-white dark:bg-indigo-500">
                S
              </span>
              Siftora
            </Link>
            <p className="mt-3 max-w-xs text-sm text-slate-500 dark:text-slate-400">
              Get notified about product updates. No spam — this is a portfolio project.
            </p>
            <div className="mt-4">
              <NewsletterForm />
            </div>
          </div>

          {FOOTER_COLUMNS.map((column) => (
            <div key={column.title}>
              <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                {column.title}
              </h3>
              <ul className="mt-3 space-y-2.5">
                {column.links.map((link) => (
                  <li key={link.label}>
                    <a
                      href={link.href}
                      className="text-sm text-slate-500 transition-colors hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100"
                    >
                      {link.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-6 text-sm text-slate-500 sm:flex-row dark:border-slate-800 dark:text-slate-400">
          <p>&copy; {new Date().getFullYear()} Siftora. All rights reserved.</p>
          <div className="flex items-center gap-4">
            {SOCIAL_LINKS.map((social) => (
              <a
                key={social.label}
                href={social.href}
                aria-label={social.label}
                className="flex size-8 items-center justify-center rounded-lg text-slate-400 transition-colors hover:bg-slate-100 hover:text-slate-900 dark:text-slate-500 dark:hover:bg-slate-800 dark:hover:text-slate-100"
              >
                <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                  {social.icon}
                </svg>
              </a>
            ))}
          </div>
        </div>
      </div>
    </footer>
  );
}
