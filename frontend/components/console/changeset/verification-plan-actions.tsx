import { Button } from "@/components/ui/button";

import type { VerificationPlanEntry } from "./verification-plan-format";

export type RecordVerificationInput = {
  taskId?: string | null;
  verificationId?: string | null;
};

export function VerificationPlanEntryActions({
  actionPending,
  entry,
  onRecordVerification,
}: {
  actionPending: boolean;
  entry: VerificationPlanEntry;
  onRecordVerification?: (input: RecordVerificationInput) => void;
}) {
  const artifactRef = entry.evidence_references.find((ref) => ref.kind === "artifact");
  return (
    <div className="mt-2 flex flex-wrap gap-2">
      <Button
        disabled={actionPending || onRecordVerification === undefined}
        onClick={() => onRecordVerification?.({ verificationId: entry.verification_id })}
        size="sm"
        type="button"
        variant="secondary"
      >
        Select
      </Button>
      <Button
        disabled
        size="sm"
        title="Command execution must use a backend endpoint."
        type="button"
        variant="outline"
      >
        Run
      </Button>
      <Button
        disabled
        size="sm"
        title="Retry requires retained failed command output."
        type="button"
        variant="outline"
      >
        Retry
      </Button>
      <Button
        disabled
        size="sm"
        title="Accepted risk requires an explicit backend risk endpoint."
        type="button"
        variant="outline"
      >
        Accept risk
      </Button>
      {artifactRef === undefined ? (
        <Button disabled size="sm" type="button" variant="ghost">
          Inspect artifact
        </Button>
      ) : (
        <Button asChild size="sm" variant="ghost">
          <a href={`#artifact-${artifactRef.ref_id}`}>Inspect artifact</a>
        </Button>
      )}
      <Button asChild size="sm" variant="ghost">
        <a href={`#evidence-claim-${entry.verification_id}`}>Evidence graph</a>
      </Button>
    </div>
  );
}
