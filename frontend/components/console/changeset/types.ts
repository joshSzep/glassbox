import type {
  ChangesetActionStatus,
  ChangesetDetailState,
  ChangesetPageState,
} from "@/stores/dashboard-stores";

export type ManualEvidenceAttachmentInput = {
  commandText?: string | null;
  evidenceKind?: "manual_command" | "external_check" | "operator_assertion" | "reviewer_note";
  freshness?: "current" | "needs_inspection" | "stale" | "unknown";
  note?: string | null;
  sourceLabel: string;
  summary: string;
};

export type ChangesetConsoleProps = {
  action?: ChangesetActionStatus;
  detail: ChangesetDetailState;
  onGenerateReviewBrief?: () => void;
  onAttachManualEvidence?: (input: ManualEvidenceAttachmentInput) => void;
  onInspectFeedbackStatus?: () => void;
  onInspectHandoff?: () => void;
  onPreviewVerification?: () => void;
  onRecordFeedbackFixup?: (feedbackId: string) => void;
  onRefresh?: () => void;
  onRefreshChangeset?: () => void;
  onSelectChangeset?: (changesetId: string) => void;
  onShowList?: () => void;
  page: ChangesetPageState;
};

export type ChangesetBadgeVariant =
  | "destructive"
  | "info"
  | "muted"
  | "outline"
  | "success"
  | "warning";
