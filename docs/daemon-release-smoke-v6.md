# Daemon Release Smoke Workflow

Use this workflow when validating persistent runtime ownership in a release
candidate or installed-wheel environment.

1. Start a daemon owner for an isolated workspace and port:

   ```bash
   glassbox daemon start --cwd /path/to/workspace --port 8765
   ```

2. Inspect owner discovery and health:

   ```bash
   glassbox daemon status --cwd /path/to/workspace
   glassbox daemon status --cwd /path/to/workspace --json
   ```

   Expected result: `Status: running`, `Health: ok`, owner metadata/log paths,
   dashboard URL, health URL, attach command, cancel command, and stop command.

3. Attach a live session while the daemon owns the workspace:

   ```bash
   glassbox session attach SESSION_ID --cwd /path/to/workspace
   ```

   Expected result: attach routes through the daemon URL. Local mutating commands
   should be rejected until the daemon is stopped.

4. Stop the daemon and confirm owner metadata is gone:

   ```bash
   glassbox daemon stop --cwd /path/to/workspace
   glassbox daemon status --cwd /path/to/workspace
   ```

   Expected result: `Stopped daemon pid ...`, followed by `Status: not running`.

## Recovery Checks

- If status is `stale`, run `glassbox daemon stop --cwd /path/to/workspace` to
  remove stale metadata, then start again or attach locally.
- If status is `running` with `Health: unreachable`, inspect the reported
  `/healthz` URL and logs, then stop and start the owner.
- If start fails because the requested port is unavailable, choose another port
  or stop the process already bound to that address.
