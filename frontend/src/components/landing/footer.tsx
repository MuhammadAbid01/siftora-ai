import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/cn";

export function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto max-w-5xl px-4 py-12 sm:px-6">
        <div className="flex flex-col items-center gap-6 text-center">
          <h2 className="text-xl font-semibold text-slate-900">Ready to see Siftora in action?</h2>
          <Link href="/sign-up" className={cn(buttonVariants({ size: "lg" }))}>
            Start Campaign
          </Link>
        </div>
        <div className="mt-10 flex flex-col items-center justify-between gap-4 border-t border-slate-200 pt-6 text-sm text-slate-500 sm:flex-row">
          <p>&copy; {new Date().getFullYear()} Siftora. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="https://github.com" className="hover:text-slate-700">
              GitHub
            </a>
            <Link href="/privacy" className="hover:text-slate-700">
              Privacy
            </Link>
            <Link href="/terms" className="hover:text-slate-700">
              Terms
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
