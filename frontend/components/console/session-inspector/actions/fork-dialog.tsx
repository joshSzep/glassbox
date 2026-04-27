import { useState } from "react";
import { GitBranch } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { SectionHeader } from "./section-header";
import { InlineActionFeedback, isBlockedByNonRetryableFailure } from "./action-feedback";
import type { SessionStreamState } from "@/api/sse";
import type { DashboardState } from "@/state/session-state";
import type { ActionStatus, DraftState } from "@/stores/dashboard-stores";

export function ForkDialog({
  action,
  data,
  drafts,
  forkDialogRequest,
  onClearForkDialogRequest,
  onFork,
  onForkLabelChange,
  pending,
  stream,
}: {
  action: ActionStatus;
  data: DashboardState;
  drafts: DraftState;
  forkDialogRequest: { requestId: number; turnId: string | null } | null;
  onClearForkDialogRequest?: () => void;
  onFork?: (input?: { branchLabel?: string | null; turnId?: string | null }) => void;
  onForkLabelChange?: (text: string) => void;
  pending: boolean;
  stream: SessionStreamState;
}) {
  const [open, setOpen] = useState(false);
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null);
  const blocked = pending || !data.canFork || isBlockedByNonRetryableFailure(action, "fork");
  const effectiveSelectedTurnId = selectedTurnId ?? forkDialogRequest?.turnId ?? null;
  const selectedTurn = data.branchableTurns.find(
    (turn) => turn.turn_id === effectiveSelectedTurnId,
  );

  function closeDialog() {
    setOpen(false);
    setSelectedTurnId(null);
    onClearForkDialogRequest?.();
  }

  function forkFrom(turnId?: string | null) {
    onFork?.({ branchLabel: drafts.forkLabel || null, turnId: turnId ?? null });
    closeDialog();
  }

  return (
    <Dialog
      onOpenChange={(nextOpen) => {
        if (nextOpen) {
          setOpen(true);
          return;
        }
        closeDialog();
      }}
      open={open || forkDialogRequest !== null}
    >
      <div className="space-y-3 rounded-md border bg-card p-3">
        <SectionHeader
          detail={
            data.forkBlockedReason ??
            "Choose a fork point and optional branch label in a focused flow."
          }
          icon={<GitBranch className="h-4 w-4" aria-hidden="true" />}
          title="Create fork"
        />
        <DialogTrigger asChild>
          <Button disabled={blocked} type="button" variant="outline">
            Create fork
          </Button>
        </DialogTrigger>
        <InlineActionFeedback action={action} data={data} kind="fork" stream={stream} />
      </div>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create fork</DialogTitle>
          <DialogDescription>
            Name the branch and choose the persisted turn where the new session should start.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium" htmlFor="fork-label">
              Fork label
            </label>
            <Input
              id="fork-label"
              onChange={(event) => onForkLabelChange?.(event.currentTarget.value)}
              placeholder="Optional branch label"
              value={drafts.forkLabel}
            />
          </div>
          <div className="grid gap-2">
            {data.branchableTurns.length > 0 ? (
              <>
                <div className="rounded-md border bg-background p-3 text-sm">
                  <Badge variant={selectedTurn === undefined ? "outline" : "info"}>
                    Selected fork point
                  </Badge>
                  <p className="mt-2 text-muted-foreground">
                    {selectedTurn === undefined
                      ? "Select a persisted turn before forking."
                      : `${selectedTurn.label} · sequence ${selectedTurn.sequence}`}
                  </p>
                </div>
                <Button
                  disabled={blocked || selectedTurn === undefined}
                  onClick={() => forkFrom(effectiveSelectedTurnId)}
                  type="button"
                >
                  Fork selected point
                </Button>
                {data.branchableTurns.map((turn) => (
                  <Button
                    aria-pressed={effectiveSelectedTurnId === turn.turn_id}
                    disabled={pending}
                    key={turn.turn_id}
                    onClick={() => {
                      setSelectedTurnId(turn.turn_id);
                    }}
                    type="button"
                    variant={effectiveSelectedTurnId === turn.turn_id ? "secondary" : "outline"}
                  >
                    Select {turn.label}
                  </Button>
                ))}
              </>
            ) : (
              <Button
                disabled={blocked}
                onClick={() => forkFrom(null)}
                type="button"
                variant="outline"
              >
                Fork latest point
              </Button>
            )}
          </div>
          {data.forkBlockedReason !== null ? (
            <p className="text-xs text-muted-foreground">{data.forkBlockedReason}</p>
          ) : null}
          <InlineActionFeedback action={action} data={data} kind="fork" stream={stream} />
        </div>
        <DialogFooter>
          <Button onClick={closeDialog} type="button" variant="ghost">
            Cancel
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
