import type { DashboardState } from "@/state/session-state";
import type { ConsoleFilters } from "@/stores/dashboard-stores";

export type QueueDescriptor = {
  countKey: keyof DashboardState["queueCounts"];
  description: string;
  label: string;
  queue: ConsoleFilters["queue"];
};

export const queueDescriptors: QueueDescriptor[] = [
  {
    countKey: "total",
    description: "Every server-prioritized session row",
    label: "All",
    queue: "all",
  },
  {
    countKey: "approvals",
    description: "Commands waiting on explicit approval",
    label: "Approvals",
    queue: "approvals",
  },
  {
    countKey: "questions",
    description: "ask_user prompts awaiting an answer",
    label: "Questions",
    queue: "questions",
  },
  {
    countKey: "failures",
    description: "Failed sessions that may need recovery",
    label: "Failures",
    queue: "failures",
  },
  {
    countKey: "degraded",
    description: "Projection or runtime health needs attention",
    label: "Degraded",
    queue: "degraded",
  },
  {
    countKey: "active",
    description: "Live work with current or recent turns",
    label: "Active",
    queue: "active",
  },
  {
    countKey: "historical",
    description: "Recent completed or archived sessions",
    label: "Historical",
    queue: "historical",
  },
];

export function queueDescriptor(queue: ConsoleFilters["queue"]): QueueDescriptor {
  return queueDescriptors.find((descriptor) => descriptor.queue === queue) ?? queueDescriptors[0];
}
