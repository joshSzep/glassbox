import type { TaskDetailState } from "@/stores/dashboard-stores";

export type TaskDetail = NonNullable<TaskDetailState["detail"]>;
export type TaskEvent = TaskDetailState["events"][number];

export type TaskEvidenceRow = {
  detail: string;
  event: TaskEvent | null;
  label: string;
  state: string;
  tone: "default" | "destructive" | "info" | "success" | "warning";
};
