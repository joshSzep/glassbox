import type { ReactNode } from "react";

export function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0 rounded-md border border-border/70 bg-surface px-3 py-2">
      <dt className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </dt>
      <dd className="mt-1 truncate text-console">{value}</dd>
    </div>
  );
}

export function Section({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="mt-4">
      <h3 className="text-sm font-semibold tracking-normal">{title}</h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

export function StateLine({
  tone = "muted",
  value,
}: {
  tone?: "destructive" | "muted";
  value: string;
}) {
  return (
    <div
      className={
        tone === "destructive"
          ? "rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          : "rounded-md border border-border/80 bg-card px-3 py-2 text-sm text-muted-foreground"
      }
    >
      {value}
    </div>
  );
}
