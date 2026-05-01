"use client";

import type { ReactNode } from "react";

export function SurfaceLink({
  children,
  current,
  href,
}: {
  children: ReactNode;
  current: boolean;
  href: string;
}) {
  return (
    <a
      aria-current={current ? "page" : undefined}
      className={`rounded-md border px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        current
          ? "border-accent bg-accent text-accent-foreground"
          : "border-border bg-surface hover:bg-surface-raised"
      }`}
      href={href}
    >
      {children}
    </a>
  );
}

export function StateLine({
  className = "",
  icon,
  tone = "muted",
  value,
}: {
  className?: string;
  icon?: ReactNode;
  tone?: "destructive" | "muted" | "warning";
  value: string;
}) {
  const toneClass =
    tone === "destructive"
      ? "border-destructive/40 text-destructive"
      : tone === "warning"
        ? "border-warning/50 text-warning-foreground"
        : "border-border/80 text-muted-foreground";
  return (
    <div className={`rounded-md border bg-card p-4 text-sm shadow-sm ${toneClass} ${className}`}>
      <span className="flex items-center gap-2">
        {icon}
        {value}
      </span>
    </div>
  );
}
