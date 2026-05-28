import type { ReactNode } from "react";

import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";

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

export function CommandList({
  commands,
}: {
  commands: { display: string; purpose: string; read_only: boolean }[];
}) {
  if (commands.length === 0) {
    return null;
  }
  return (
    <DataList density="compact">
      {commands.slice(0, 6).map((command) => (
        <DataListItem key={command.display}>
          <DataListLabel className="break-all">{command.display}</DataListLabel>
          <DataListMeta>
            {command.purpose} {command.read_only ? "(read-only)" : "(explicit mutation)"}
          </DataListMeta>
        </DataListItem>
      ))}
    </DataList>
  );
}

export function NonClaims({ claims }: { claims: string[] }) {
  if (claims.length === 0) {
    return null;
  }
  return (
    <ul className="grid gap-1 text-console text-muted-foreground">
      {claims.slice(0, 4).map((claim) => (
        <li key={claim}>{claim}</li>
      ))}
    </ul>
  );
}

export function custodyVariant(state: string) {
  if (state === "accepted" || state === "accepted-for-follow-up") {
    return "success" as const;
  }
  if (state === "rejected") {
    return "destructive" as const;
  }
  if (state === "archived") {
    return "muted" as const;
  }
  return "info" as const;
}

export function readinessVariant(state: string) {
  if (state === "ready") {
    return "success" as const;
  }
  if (state === "blocked" || state === "failed-needs-triage") {
    return "destructive" as const;
  }
  if (state === "needs-verification" || state === "local-only-evidence") {
    return "warning" as const;
  }
  return "info" as const;
}

export function redactionVariant(state: string) {
  if (state === "reviewer-safe" || state === "redacted") {
    return "success" as const;
  }
  if (state === "raw-included") {
    return "destructive" as const;
  }
  if (state === "local-only-omitted") {
    return "warning" as const;
  }
  return "muted" as const;
}

export function compatibilityVariant(state: string) {
  if (state === "supported") {
    return "success" as const;
  }
  if (state === "supported-with-warnings" || state === "legacy-inspection-only") {
    return "warning" as const;
  }
  if (state === "unsupported" || state === "invalid" || state === "future-version") {
    return "destructive" as const;
  }
  return "muted" as const;
}
