import type { LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";

export function StatePanel({
  icon: Icon,
  title,
  tone,
  value,
}: {
  icon: LucideIcon;
  title: string;
  tone: "destructive" | "info" | "success";
  value: string;
}) {
  return (
    <section className="grid min-h-80 place-items-center rounded-md border border-border/80 bg-card p-8 text-center text-card-foreground shadow-sm">
      <div className="max-w-sm">
        <Badge variant={tone === "destructive" ? "destructive" : tone}>
          <Icon className={operatorIconSizeClass} aria-hidden="true" />
          {title}
        </Badge>
        <p className="mt-4 text-sm text-muted-foreground">{value}</p>
      </div>
    </section>
  );
}
