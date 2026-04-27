import { ListChecks } from "lucide-react";

import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";
import { Pane } from "@/components/console/session-inspector/frame";
import type { DashboardState } from "@/state/session-state";

export function ActionSummaryPane({ data }: { data: DashboardState }) {
  return (
    <Pane icon={ListChecks} title="Actions">
      <DataList density="compact">
        {data.pendingApprovals.map((approval) => (
          <DataListItem key={approval.approval_id}>
            <DataListLabel>{approval.subject}</DataListLabel>
            <DataListMeta>{approval.reason}</DataListMeta>
          </DataListItem>
        ))}
        {data.pendingQuestionId !== null ? (
          <DataListItem>
            <DataListLabel>Question {data.pendingQuestionId}</DataListLabel>
            <DataListMeta>{data.pendingQuestionText ?? "Awaiting operator answer"}</DataListMeta>
          </DataListItem>
        ) : null}
        {data.activeToolCalls.map((tool) => (
          <DataListItem key={tool.tool_call_id}>
            <DataListLabel>{tool.tool_name}</DataListLabel>
            <DataListMeta>{tool.summary ?? tool.status}</DataListMeta>
          </DataListItem>
        ))}
        {data.pendingApprovals.length === 0 &&
        data.pendingQuestionId === null &&
        data.activeToolCalls.length === 0 ? (
          <DataListItem>
            <DataListMeta>No active approvals, questions, or tool calls.</DataListMeta>
          </DataListItem>
        ) : null}
      </DataList>
    </Pane>
  );
}
