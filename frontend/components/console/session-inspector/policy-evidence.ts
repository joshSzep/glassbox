import type { BadgeProps } from "@/components/ui/badge";

export function policyDecisionLabel(
  outcome?: string | null,
  sourceKind?: string | null,
): string | null {
  if (!outcome) {
    return null;
  }
  if (outcome === "approve") {
    return "approval required";
  }
  if (outcome === "deny") {
    return "denied by policy";
  }
  if (outcome === "blocked" && sourceKind === "invariant") {
    return "invariant block";
  }
  if (outcome === "blocked") {
    return "blocked by policy";
  }
  if (outcome === "allow") {
    return "advisory risk accepted";
  }
  return outcome;
}

export function policyDecisionVariant(
  outcome?: string | null,
  sourceKind?: string | null,
): BadgeProps["variant"] {
  if (outcome === "deny" || outcome === "blocked") {
    return "destructive";
  }
  if (outcome === "approve") {
    return "warning";
  }
  if (outcome === "allow" && sourceKind === "rule") {
    return "success";
  }
  if (outcome === "allow") {
    return "info";
  }
  return "outline";
}

export function policyRiskLabel(riskLevel?: string | null): string | null {
  return riskLevel ? `${riskLevel} risk` : null;
}

export function policySourceLabel(
  sourceKind?: string | null,
  sourceLabel?: string | null,
): string | null {
  if (sourceKind && sourceLabel) {
    return `${sourceKind}:${sourceLabel}`;
  }
  return sourceLabel ?? sourceKind ?? null;
}
