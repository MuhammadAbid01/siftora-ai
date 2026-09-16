"use client";

import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { cn } from "@/lib/cn";

/**
 * Minimal accessible dropdown menu (trigger + popover), hand-rolled to
 * match the rest of the UI kit rather than pulling in a menu library.
 * Closes on outside click, Escape, or item selection; supports basic
 * arrow-key roving focus between menu items.
 */
export function DropdownMenu({
  trigger,
  children,
  align = "end",
  className,
}: {
  trigger: (props: { open: boolean }) => ReactNode;
  children: ReactNode;
  align?: "start" | "end";
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (rootRef.current && !rootRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKeyDown = (event: globalThis.KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  const handleMenuKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    const root = rootRef.current;
    if (!root) return;
    const items = Array.from(
      root.querySelectorAll<HTMLElement>('[role="menuitem"]:not([disabled])'),
    );
    if (items.length === 0) return;
    const currentIndex = items.indexOf(document.activeElement as HTMLElement);
    const nextIndex =
      event.key === "ArrowDown"
        ? (currentIndex + 1) % items.length
        : (currentIndex - 1 + items.length) % items.length;
    items[nextIndex]?.focus();
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        {trigger({ open })}
      </button>
      {open && (
        <div
          role="menu"
          onKeyDown={handleMenuKeyDown}
          onClick={() => setOpen(false)}
          className={cn(
            "absolute z-40 mt-2 min-w-48 rounded-xl border border-slate-200 bg-white p-1.5 shadow-lg motion-safe:animate-scale-in dark:border-slate-800 dark:bg-slate-900",
            align === "end" ? "right-0" : "left-0",
            className,
          )}
          style={{ transformOrigin: align === "end" ? "top right" : "top left" }}
        >
          {children}
        </div>
      )}
    </div>
  );
}

export function DropdownMenuItem({
  children,
  onSelect,
  href,
  className,
  destructive,
}: {
  children: ReactNode;
  onSelect?: () => void;
  href?: string;
  className?: string;
  destructive?: boolean;
}) {
  const sharedClassName = cn(
    "flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm font-medium transition-colors duration-100 motion-reduce:transition-none",
    destructive
      ? "text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-500/10"
      : "text-slate-700 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800",
    className,
  );

  if (href) {
    return (
      <a href={href} role="menuitem" className={sharedClassName}>
        {children}
      </a>
    );
  }

  return (
    <button type="button" role="menuitem" onClick={onSelect} className={sharedClassName}>
      {children}
    </button>
  );
}

export function DropdownMenuSeparator() {
  return <div role="separator" className="my-1.5 h-px bg-slate-200 dark:bg-slate-800" />;
}

export function DropdownMenuLabel({ children }: { children: ReactNode }) {
  return (
    <div className="px-2.5 py-1.5 text-xs font-medium text-slate-500 dark:text-slate-400">
      {children}
    </div>
  );
}
