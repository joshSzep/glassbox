import { spawnSync } from "node:child_process";
import path from "node:path";

const frontendRoot = process.cwd();
const repoRoot = path.resolve(frontendRoot, "..");

const checks = [
  { args: ["format:check"], command: "pnpm", cwd: frontendRoot, label: "frontend format" },
  { args: ["lint"], command: "pnpm", cwd: frontendRoot, label: "frontend lint" },
  { args: ["typecheck"], command: "pnpm", cwd: frontendRoot, label: "frontend typecheck" },
  { args: ["test"], command: "pnpm", cwd: frontendRoot, label: "frontend unit/component" },
  { args: ["test:e2e"], command: "pnpm", cwd: frontendRoot, label: "browser workflows" },
  {
    args: ["screenshots:v4-audit"],
    command: "pnpm",
    cwd: frontendRoot,
    label: "v4 screenshot archive",
  },
  { args: ["build"], command: "pnpm", cwd: frontendRoot, label: "static export" },
  {
    args: [
      "run",
      "pytest",
      "tests/integration/test_web_bootstrap.py",
      "tests/integration/test_web_spa_static.py",
      "tests/integration/test_web_session_aggregate.py",
      "tests/integration/test_web_session_snapshot.py",
      "tests/integration/test_web_session_interaction.py",
      "tests/integration/test_web_approval_resolution.py",
      "tests/integration/test_web_fork.py",
      "tests/integration/test_web_sse_events.py",
      "tests/integration/test_web_session_index.py",
      "tests/integration/test_web_chat_dashboard_live.py",
    ],
    command: "uv",
    cwd: repoRoot,
    label: "python web/dashboard integration",
  },
];

for (const check of checks) {
  console.log(`\n==> ${check.label}`);
  const result = spawnSync(check.command, check.args, {
    cwd: check.cwd,
    env: process.env,
    stdio: "inherit",
  });

  if (result.status !== 0) {
    console.error(`\nV4 UX release gate failed: ${check.label}`);
    process.exit(result.status ?? 1);
  }
}

console.log("\nV4 UX release gate passed.");
