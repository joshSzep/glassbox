export function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function shortId(value) {
  if (!value) {
    return "unknown";
  }
  return String(value).slice(0, 8);
}

export function renderEmpty(message) {
  return `<p class="empty">${escHtml(message)}</p>`;
}

export function renderStatusChip(status) {
  const statusText = status ? String(status) : "unknown";
  return `<span class="status-chip status-chip-${escHtml(statusText)}">${escHtml(statusText.replaceAll("_", " "))}</span>`;
}

export function renderGuidanceChip(tone, label) {
  return `<span class="guidance-chip guidance-chip-${escHtml(tone)}">${escHtml(label)}</span>`;
}
