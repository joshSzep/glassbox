import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";

export function InspectorFrame({ children }: { children: ReactNode }) {
  return (
    <aside
      className="min-w-0 rounded-lg border bg-card text-card-foreground shadow-sm"
      aria-label="Selected session inspector"
    >
      {children}
    </aside>
  );
}

export function Pane({
  children,
  icon: Icon,
  title,
}: {
  children: ReactNode;
  icon: LucideIcon;
  title: string;
}) {
  return (
    <section className="rounded-lg border bg-background p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
        <Icon className={operatorIconSizeClass} aria-hidden="true" />
        {title}
      </h3>
      {children}
    </section>
  );
}

export function StateBlock({
  icon: Icon,
  title,
  value,
  variant,
}: {
  icon: LucideIcon;
  title: string;
  value: string;
  variant: "destructive" | "info" | "muted";
}) {
  return (
    <div className="grid min-h-80 place-items-center p-8 text-center">
      <div className="max-w-sm">
        <Badge variant={variant}>
          <Icon className={operatorIconSizeClass} aria-hidden="true" />
          {title}
        </Badge>
        <p className="mt-4 text-sm text-muted-foreground">{value}</p>
      </div>
    </div>
  );
}

export function EmptyLine({ value }: { value: string }) {
  return <p className="text-sm text-muted-foreground">{value}</p>;
}
