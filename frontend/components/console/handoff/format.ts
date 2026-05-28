export function custodyVariant(state: string) {
  if (state === "accepted" || state === "accepted-for-follow-up") {
    return "success" as const;
  }
  if (state === "rejected") {
    return "destructive" as const;
  }
  if (state === "archived") {
    return "muted" as const;
  }
  return "info" as const;
}

export function readinessVariant(state: string) {
  if (state === "ready") {
    return "success" as const;
  }
  if (state === "blocked" || state === "failed-needs-triage") {
    return "destructive" as const;
  }
  if (state === "needs-verification" || state === "local-only-evidence") {
    return "warning" as const;
  }
  return "info" as const;
}

export function redactionVariant(state: string) {
  if (state === "reviewer-safe" || state === "redacted") {
    return "success" as const;
  }
  if (state === "raw-included") {
    return "destructive" as const;
  }
  if (state === "local-only-omitted") {
    return "warning" as const;
  }
  return "muted" as const;
}

export function compatibilityVariant(state: string) {
  if (state === "supported") {
    return "success" as const;
  }
  if (state === "supported-with-warnings" || state === "legacy-inspection-only") {
    return "warning" as const;
  }
  if (state === "unsupported" || state === "invalid" || state === "future-version") {
    return "destructive" as const;
  }
  return "muted" as const;
}
