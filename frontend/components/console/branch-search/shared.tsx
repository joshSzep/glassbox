"use client";

import type { ReactNode } from "react";
import { AlertCircle } from "lucide-react";

import { operatorIconSizeClass } from "@/design-system/operator-status";

export function StateLine({
  icon,
  tone = "muted",
  value,
}: {
  icon?: ReactNode;
  tone?: "destructive" | "muted";
  value: string;
}) {
  const toneClass =
    tone === "destructive"
      ? "border-destructive/40 text-destructive"
      : "border-border/80 text-muted-foreground";
  return (
    <div className={`rounded-md border bg-card p-4 text-sm shadow-sm ${toneClass}`}>
      <span className="flex items-center gap-2">
        {icon ?? <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
        {value}
      </span>
    </div>
  );
}
