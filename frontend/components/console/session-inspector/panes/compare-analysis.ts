import { formatDuration } from "@/components/console/session-inspector/format";
import { policyRiskLabel } from "@/components/console/session-inspector/policy-evidence";
import type { ActiveToolCall, DashboardState, PolicySummary } from "@/state/session-state";

import { summarizeTurnMetrics } from "./shared";

export type ComparableSnapshot = DashboardState | NonNullable<DashboardState["compareSession"]>;

export type CompareFact = {
  label: string;
  value: string;
};

export type CompareAnalysis = ReturnType<typeof buildCompareAnalysis>;

export function buildCompareAnalysis(
  current: DashboardState,
  compare: NonNullable<DashboardState["compareSession"]>,
) {
  const workingSetDelta = compareStringSets(
    current.runtimeContext?.working_set?.items?.map((item) => item.subject) ?? [],
    compare.runtimeContext?.working_set?.items?.map((item) => item.subject) ?? [],
  );
  const runtimePathDelta = compareStringSets(
    current.runtimeContext?.repository_context.high_signal_paths ?? [],
    compare.runtimeContext?.repository_context.high_signal_paths ?? [],
  );
  const currentLatest = current.transcript.at(-1);
  const compareLatest = compare.transcript.at(-1);
  const transcript = compareTranscript(current.transcript, compare.transcript);
  const currentTotals = summarizeTurnMetrics(current.turnMetrics);
  const compareTotals = summarizeTurnMetrics(compare.turnMetrics);

  return {
    branch: {
      compared: branchFacts(compare),
      current: branchFacts(current),
    },
    policy: {
      compared: policyFacts(compare),
      current: policyFacts(current),
    },
    runtime: {
      compared: runtimeProjectionFacts(
        compare,
        runtimePathDelta.comparedOnly,
        workingSetDelta.comparedOnly,
      ),
      current: runtimeProjectionFacts(
        current,
        runtimePathDelta.currentOnly,
        workingSetDelta.currentOnly,
      ),
    },
    summary: [
      {
        label: "Status change",
        value:
          current.status === compare.status
            ? `both ${current.status}`
            : `${compare.status} compared -> ${current.status} current`,
      },
      {
        label: "Transcript divergence",
        value: `${transcript.shared.length} shared · ${transcript.currentOnly.length} current-only · ${transcript.comparedOnly.length} compared-only`,
      },
      {
        label: "Latest message",
        value:
          currentLatest === undefined || compareLatest === undefined
            ? "latest message unavailable in one snapshot"
            : currentLatest.message_id === compareLatest.message_id
              ? "same latest message id"
              : `${compareLatest.role} compared -> ${currentLatest.role} current`,
      },
      {
        label: "Tool activity",
        value: `${currentTotals.toolCalls} current tool calls · ${compareTotals.toolCalls} compared tool calls · ${currentTotals.failedToolCalls - compareTotals.failedToolCalls} failed-tool delta`,
      },
      {
        label: "Policy outcomes",
        value: `${formatPolicySummary(current.sessionPolicySummary)} current · ${formatPolicySummary(compare.sessionPolicySummary)} compared`,
      },
      {
        label: "Runtime context",
        value: `${runtimePathDelta.currentOnly.length} current-only paths · ${runtimePathDelta.comparedOnly.length} compared-only paths`,
      },
      {
        label: "Working set",
        value: `${workingSetDelta.currentOnly.length} current-only items · ${workingSetDelta.comparedOnly.length} compared-only items`,
      },
      {
        label: "Turn summaries",
        value: `${current.turnMetrics.length} current metrics · ${compare.turnMetrics.length} compared metrics`,
      },
      {
        label: "Fork source",
        value: `current ${current.forkedFromTurnId ?? "none"} · compared ${compare.forkedFromTurnId ?? "none"}`,
      },
    ],
    tools: {
      compared: toolFacts(compare),
      current: toolFacts(current),
    },
    transcript,
  };
}

function branchFacts(session: ComparableSnapshot): CompareFact[] {
  return [
    { label: "Session", value: session.sessionId ?? "unknown session" },
    { label: "Status", value: session.status },
    { label: "Branch", value: session.branchLabel ?? "unlabeled branch" },
    { label: "Parent", value: session.parentSessionId ?? "none" },
    { label: "Fork turn", value: session.forkedFromTurnId ?? "none" },
    {
      label: "Fork sequence",
      value: session.forkedFromSequence === null ? "none" : String(session.forkedFromSequence),
    },
    { label: "Last sequence", value: String(session.lastSequence) },
  ];
}

function toolFacts(session: ComparableSnapshot): CompareFact[] {
  const totals = summarizeTurnMetrics(session.turnMetrics);
  return [
    { label: "Active tools", value: formatToolCalls(session.activeToolCalls) },
    { label: "Metric rows", value: String(session.turnMetrics.length) },
    { label: "Tool calls", value: String(totals.toolCalls) },
    { label: "Failed tools", value: String(totals.failedToolCalls) },
    { label: "Tool duration", value: formatDuration(totals.toolDurationMs) },
    { label: "Turn duration", value: formatDuration(totals.turnDurationMs) },
  ];
}

function policyFacts(session: ComparableSnapshot): CompareFact[] {
  const summary = session.sessionPolicySummary;
  const currentTurn = session.currentTurnPolicySummary;
  return [
    { label: "Session decisions", value: formatPolicySummary(summary) },
    { label: "Highest risk", value: policyRiskLabel(summary?.highest_risk_level) ?? "no risk" },
    { label: "Approvals", value: String(summary?.approve_count ?? 0) },
    { label: "Denied", value: String(summary?.deny_count ?? 0) },
    { label: "Blocked", value: String(summary?.blocked_count ?? 0) },
    { label: "Pending approvals", value: String(session.pendingApprovals.length) },
    { label: "Current-turn decisions", value: formatPolicySummary(currentTurn) },
  ];
}

function runtimeProjectionFacts(
  session: ComparableSnapshot,
  pathDelta: string[],
  workingSetDelta: string[],
): CompareFact[] {
  const projection = session.projectionHealth;
  return [
    {
      label: "Projection",
      value: projection === null ? "unavailable" : `${projection.state} · lag ${projection.lag}`,
    },
    {
      label: "Runtime owner",
      value: session.runtimeContext?.repository_context.workspace_name ?? "unknown",
    },
    {
      label: "High-signal paths",
      value: String(session.runtimeContext?.repository_context.high_signal_paths?.length ?? 0),
    },
    { label: "Only here paths", value: pathDelta.length === 0 ? "none" : pathDelta.join(", ") },
    {
      label: "Working-set items",
      value: String(session.runtimeContext?.working_set?.items?.length ?? 0),
    },
    {
      label: "Only here working set",
      value: workingSetDelta.length === 0 ? "none" : workingSetDelta.join(", "),
    },
  ];
}

export function compareTranscript(
  current: DashboardState["transcript"],
  compared: DashboardState["transcript"],
) {
  const currentIds = new Set(current.map((message) => message.message_id));
  const comparedIds = new Set(compared.map((message) => message.message_id));
  return {
    comparedOnly: compared.filter((message) => !currentIds.has(message.message_id)),
    currentOnly: current.filter((message) => !comparedIds.has(message.message_id)),
    shared: current.filter((message) => comparedIds.has(message.message_id)),
  };
}

function formatToolCalls(toolCalls: ActiveToolCall[]): string {
  if (toolCalls.length === 0) {
    return "none";
  }
  return toolCalls
    .map((toolCall) => `${toolCall.tool_name} ${toolCall.status}`)
    .slice(0, 3)
    .join(", ");
}

export function formatPolicySummary(summary: PolicySummary | null): string {
  if (summary === null || summary.total_decisions === 0) {
    return "no decisions";
  }
  return `${summary.total_decisions} total, ${summary.allow_count} allowed, ${summary.approve_count} approval, ${summary.deny_count} denied, ${summary.blocked_count} blocked`;
}

export function compareStringSets(current: string[], compared: string[]) {
  const currentSet = new Set(current);
  const comparedSet = new Set(compared);
  return {
    comparedOnly: compared.filter((value) => !currentSet.has(value)),
    currentOnly: current.filter((value) => !comparedSet.has(value)),
  };
}
