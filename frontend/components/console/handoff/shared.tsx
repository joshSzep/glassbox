import type { ReactNode } from "react";

export function CockpitPanel({ children, title }: { children: ReactNode; title: string }) {
  return (
    <section className="rounded-md border border-border/80 bg-card p-4 text-card-foreground shadow-sm">
      <h2 className="text-sm font-semibold tracking-normal">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function Field({
  children,
  className,
  label,
}: {
  children: ReactNode;
  className?: string;
  label: string;
}) {
  return (
    <label className={`grid gap-1 ${className ?? ""}`}>
      <span className="text-xs font-medium uppercase tracking-normal text-muted-foreground">
        {label}
      </span>
      {children}
    </label>
  );
}

export function Select<T extends string>({
  onChange,
  options,
  value,
}: {
  onChange: (value: T) => void;
  options: T[];
  value: T;
}) {
  return (
    <select
      className="flex h-9 w-full rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      onChange={(event) => onChange(event.target.value as T)}
      value={value}
    >
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

export function StateLine({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: "destructive" | "muted";
}) {
  return (
    <p
      className={
        tone === "destructive"
          ? "rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive"
          : "rounded-md border border-border/80 bg-surface px-3 py-2 text-sm text-muted-foreground"
      }
    >
      {children}
    </p>
  );
}
