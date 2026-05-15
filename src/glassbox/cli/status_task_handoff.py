"""Task handoff-readiness formatting helpers for the CLI."""

from glassbox.core import HandoffReadiness


def print_task_handoff_readiness(readiness: HandoffReadiness) -> None:
    print(f"Task handoff readiness: {readiness.source.primary_id}")
    print(f"Intent: {readiness.intent.value}")
    print(f"State: {readiness.state.value}")
    print(f"Confidence: {readiness.confidence.value}")
    print(f"Freshness: {readiness.freshness.value}")
    if readiness.reasons:
        print("Reasons:")
        for reason in readiness.reasons:
            print(f"  - {reason.kind.value}: {reason.summary}")
    if readiness.limitations:
        print("Limitations:")
        for limitation in readiness.limitations:
            print(f"  - {limitation}")
    if readiness.missing_evidence:
        print("Missing evidence:")
        for item in readiness.missing_evidence:
            print(f"  - {item.summary}")
    if readiness.stale_evidence:
        print("Stale evidence:")
        for item in readiness.stale_evidence:
            print(f"  - {item.summary}")
    if readiness.local_only_evidence:
        print("Local-only evidence:")
        for item in readiness.local_only_evidence:
            print(f"  - {item.summary}")
    if readiness.accepted_risks:
        print("Accepted risks:")
        for item in readiness.accepted_risks:
            print(f"  - {item.summary}")
    print("Safe first commands:")
    for command in readiness.safe_first_commands:
        print(f"  - {command.display}")
    print("Non-claims:")
    for non_claim in readiness.non_claims:
        print(f"  - {non_claim}")


__all__ = ["print_task_handoff_readiness"]
