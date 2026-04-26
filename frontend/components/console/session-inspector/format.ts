import type { TranscriptMessage } from "@/state/session-state";

export function formatMessage(message: TranscriptMessage): string {
  return message.parts.map((part) => part.text).join("\n");
}

export function formatDuration(value: number | null): string {
  if (value === null) {
    return "duration unknown";
  }
  if (value < 1000) {
    return `${value}ms`;
  }
  return `${(value / 1000).toFixed(1)}s`;
}

export function formatTime(value: string | null): string {
  if (value === null) {
    return "time unknown";
  }
  return value.replace("T", " ").replace("Z", " UTC");
}
