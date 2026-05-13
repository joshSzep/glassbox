import {
  AlertTriangle,
  ClipboardCheck,
  FileSearch,
  ShieldCheck,
  Wrench,
  type LucideIcon,
} from "lucide-react";

import type { BadgeProps } from "@/components/ui/badge";
import type { DashboardState, OperatorQueueItem } from "@/state/session-state";

export type QueueLane = {
  count: (data: DashboardState) => number;
  description: string;
  families: OperatorQueueItem["family"][];
  icon: LucideIcon;
  label: string;
  variant: NonNullable<BadgeProps["variant"]>;
};

export const queueLanes: QueueLane[] = [
  {
    count: (data) => data.operatorQueueCounts.work_blocking,
    description: "Blocked turns, approvals, questions, and failed active work.",
    families: ["work_blocking"],
    icon: AlertTriangle,
    label: "Action Needed",
    variant: "warning",
  },
  {
    count: (data) => data.operatorQueueCounts.verification_blocking,
    description: "Failed, stale, skipped, or missing confidence evidence.",
    families: ["verification_blocking"],
    icon: ClipboardCheck,
    label: "Verification",
    variant: "info",
  },
  {
    count: (data) => data.operatorQueueCounts.review_blocking,
    description: "Review handoff blockers and response-linked fixup evidence.",
    families: ["review_blocking"],
    icon: FileSearch,
    label: "Review",
    variant: "warning",
  },
  {
    count: (data) => data.operatorQueueCounts.maintenance,
    description: "Runtime, projection, repository, artifact, and job upkeep.",
    families: ["maintenance"],
    icon: Wrench,
    label: "Maintenance",
    variant: "outline",
  },
  {
    count: (data) => data.operatorQueueCounts.advisory + data.operatorQueueCounts.informational,
    description: "Useful context, watch items, and non-blocking recommendations.",
    families: ["advisory", "informational"],
    icon: ShieldCheck,
    label: "Advisory",
    variant: "muted",
  },
];
