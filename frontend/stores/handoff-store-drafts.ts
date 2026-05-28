import type { HandoffDraftState, HandoffStoreState } from "@/stores/handoff-store";

export function createDefaultHandoffDrafts(): HandoffDraftState {
  return {
    decisionActor: "operator",
    decisionReason: "",
    expectedCustodian: "",
    exportedBy: "operator",
    followUpIntent: "verification-needed",
    intent: "review-only",
    markdownOutputPath: "",
    note: "",
    outputFormat: "json",
    outputPath: "",
    packagePath: "",
    recipient: "",
    sourceId: "",
    sourceKind: "session",
  };
}

export function optionalText(value: string): string | null {
  const trimmed = value.trim();
  return trimmed.length === 0 ? null : trimmed;
}

export function needsSourceId(sourceKind: HandoffDraftState["sourceKind"]): boolean {
  return sourceKind !== "workspace" && sourceKind !== "release";
}

export function sourceIdForRequest(drafts: HandoffDraftState): string {
  if (!needsSourceId(drafts.sourceKind)) {
    return drafts.sourceKind;
  }
  const sourceId = drafts.sourceId.trim();
  if (sourceId.length === 0) {
    throw new Error("Choose a session, task, or changeset id before requesting handoff details.");
  }
  return sourceId;
}

export function requirePackagePath(get: () => HandoffStoreState): string {
  const packagePath = get().drafts.packagePath.trim();
  if (packagePath.length === 0) {
    throw new Error("Enter a local handoff package path before package inspection.");
  }
  return packagePath;
}

export function sourceKindDraft(
  sourceKind: string,
  fallback: HandoffDraftState["sourceKind"],
): HandoffDraftState["sourceKind"] {
  return sourceKind === "changeset" ||
    sourceKind === "release" ||
    sourceKind === "session" ||
    sourceKind === "task" ||
    sourceKind === "workspace"
    ? sourceKind
    : fallback;
}
