import { spawnSync } from "node:child_process";

const args = process.argv.slice(2);
const env = { ...process.env };
const passthrough = [];

for (let index = 0; index < args.length; index += 1) {
  const arg = args[index];
  if (arg === "--") {
    continue;
  }
  if (arg === "--scenario") {
    const scenario = args[index + 1];
    if (scenario === undefined) {
      console.error("Missing value for --scenario");
      process.exit(2);
    }
    env.V4_AUDIT_SCENARIO = scenario;
    index += 1;
    continue;
  }
  if (arg.startsWith("--scenario=")) {
    env.V4_AUDIT_SCENARIO = arg.slice("--scenario=".length);
    continue;
  }
  passthrough.push(arg);
}

const revision = spawnSync("git", ["rev-parse", "--short", "HEAD"], {
  encoding: "utf8",
});
if (revision.status === 0) {
  env.V4_AUDIT_REVISION = revision.stdout.trim();
}

const result = spawnSync(
  "pnpm",
  ["exec", "playwright", "test", "--config", "playwright.screenshots.config.ts", ...passthrough],
  {
    env,
    stdio: "inherit",
  },
);

process.exit(result.status ?? 1);
