import type { ReactNode } from "react";
import { AlertCircle, CheckCircle2, Clock3, FileSearch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { operatorIconSizeClass } from "@/design-system/operator-status";

export function TaskState({
  icon,
  title,
  tone = "default",
  value,
}: {
  icon?: ReactNode;
  title: string;
  tone?: "default" | "destructive";
  value: string;
}) {
  return (
    <section
      aria-label={title}
      className={`rounded-md border p-4 shadow-sm ${
        tone === "destructive"
          ? "border-destructive/40 bg-destructive/10 text-destructive"
          : "border-border/80 bg-card text-card-foreground"
      }`}
    >
      <div className="flex items-start gap-3">
        {icon ?? <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />}
        <div className="min-w-0">
          <h2 className="text-sm font-semibold tracking-normal">{title}</h2>
          <p className="mt-1 break-words text-sm text-muted-foreground">{value}</p>
        </div>
      </div>
    </section>
  );
}

export function TaskStatusBadge({ blocked, status }: { blocked: boolean; status: string }) {
  if (blocked) {
    return (
      <Badge variant="warning">
        <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />
        Blocked
      </Badge>
    );
  }
  if (status === "failed") {
    return (
      <Badge variant="destructive">
        <AlertCircle className={operatorIconSizeClass} aria-hidden="true" />
        Failed
      </Badge>
    );
  }
  if (status === "completed") {
    return (
      <Badge variant="success">
        <CheckCircle2 className={operatorIconSizeClass} aria-hidden="true" />
        Completed
      </Badge>
    );
  }
  if (status === "cancelled" || status === "abandoned") {
    return (
      <Badge variant="muted">
        <Clock3 className={operatorIconSizeClass} aria-hidden="true" />
        Historical
      </Badge>
    );
  }
  return (
    <Badge variant="info">
      <FileSearch className={operatorIconSizeClass} aria-hidden="true" />
      {status}
    </Badge>
  );
}
