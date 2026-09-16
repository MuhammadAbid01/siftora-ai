import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export default function NotFound() {
  return (
    <div className="flex min-h-full flex-1 flex-col items-center justify-center gap-4 px-4 py-24 text-center motion-safe:animate-fade-in">
      <span className="flex size-12 items-center justify-center rounded-2xl bg-indigo-50 text-2xl font-bold text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
        ?
      </span>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900 dark:text-slate-100">
        Page not found
      </h1>
      <p className="max-w-sm text-sm text-slate-500 dark:text-slate-400">
        The page you&apos;re looking for doesn&apos;t exist or may have been moved.
      </p>
      <Link href="/" className={cn(buttonVariants({ size: "sm" }))}>
        Back to home
      </Link>
    </div>
  );
}
