import type { LucideIcon } from "lucide-react";
import {
  AlertCircle,
  Bell,
  CheckCircle2,
  CircleHelp,
  CircleSlash,
  Clock3,
  GitBranch,
  RadioTower,
  RefreshCcw,
} from "lucide-react";

import type { BadgeProps } from "@/components/ui/badge";

export type OperatorStatusTone = "danger" | "info" | "muted" | "success" | "warning";

export type OperatorStatusToken = {
  badgeVariant: NonNullable<BadgeProps["variant"]>;
  icon: LucideIcon;
  label: string;
};

export const operatorStatusTokens = {
  actionNeeded: { badgeVariant: "warning", icon: Bell, label: "Action needed" },
  active: { badgeVariant: "success", icon: RadioTower, label: "Active" },
  approval: { badgeVariant: "warning", icon: CheckCircle2, label: "Approval" },
  degraded: { badgeVariant: "warning", icon: RefreshCcw, label: "Degraded" },
  failed: { badgeVariant: "destructive", icon: AlertCircle, label: "Failed" },
  historical: { badgeVariant: "muted", icon: Clock3, label: "Historical" },
  lineage: { badgeVariant: "info", icon: GitBranch, label: "Lineage" },
  question: { badgeVariant: "info", icon: CircleHelp, label: "Question" },
  unknown: { badgeVariant: "outline", icon: CircleSlash, label: "Unknown" },
} satisfies Record<string, OperatorStatusToken>;

export const operatorIconSizeClass = "h-4 w-4";
