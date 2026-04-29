# v8 Network And Browser Diagnostic Tool Contract

For the docs hub and operator guides, start at [README.md](./README.md). Pair
this contract with [tool-expansion-v8.md](./tool-expansion-v8.md),
[tool-policy.md](./tool-policy.md), and [frontend-testing.md](./frontend-testing.md).

This document records the GBX-875 contract for optional network and browser
diagnostic tools. The decision for v8 is conservative: Glassbox may add tightly
bounded local diagnostics for app workflows, but it must not grow general web
automation, credentialed scraping, remote exploitation, or browser-native code
editing.

## Accepted Use Cases

The accepted v8 use cases are local workflow diagnostics:

- local dev server health checks for `localhost`, `127.0.0.1`, `::1`, and operator-approved loopback ports
- HTTP endpoint checks for local APIs, including status code, content type, latency, redirect posture, and bounded response preview
- static asset verification for locally served dashboard or app builds
- screenshot capture of local app routes for retained visual evidence
- accessibility smoke checks against local routes using a documented engine
- console-error and network-error summaries for local frontend workflows
- production static-dashboard verification through the FastAPI-served path

Remote hosts are not part of the default tool contract. A later task may allow
remote diagnostics only behind explicit operator opt-in, host allowlists, timeout
budgets, and redaction rules.

## Policy Contract

Network and browser diagnostics need their own policy layer even when they are
read-only. A request can leak local content, hit credentialed dev services, or
turn into broad web automation if host and output boundaries are vague.

Required controls:

- default host allowlist: `localhost`, `127.0.0.1`, and `::1`
- optional repository/operator allowlist for exact hosts, ports, and schemes
- explicit approval for any non-loopback host
- timeout budget per request and per diagnostic run
- maximum redirect count
- response body byte limit and content-type allowlist
- screenshot/artifact byte limit
- secret redaction for headers, cookies, URLs, local storage, console output, response previews, and accessibility reports
- no credential injection by default
- no form submission, destructive HTTP methods, file upload, or arbitrary script execution in the first slice
- canonical event summaries plus retained artifacts for screenshots or large reports
- cancellation and retry behavior that records durable stop evidence

Initial risk posture:

| Diagnostic | Default risk | Required gate |
| --- | --- | --- |
| Local HTTP health check | `read_only` plus network-local policy | Loopback allowlist, timeout, response byte limit |
| Local static asset check | `read_only` plus network-local policy | Loopback/file path scope, artifact byte limit |
| Local screenshot capture | `read_only` plus artifact policy | Loopback allowlist, viewport limits, screenshot artifact redaction |
| Local accessibility smoke | `read_only` plus command/browser policy | Loopback allowlist, timeout, report artifact redaction |
| Remote HTTP check | Approval-gated network diagnostic | Exact host allowlist, approval, timeout, redaction |
| General browsing | Not accepted | Non-goal for v8 |

## Prototype Schema

A later implementation should prefer narrow tools over a general browser remote
control surface.

Candidate schemas:

```text
local_http_check
  url: http://localhost:PORT/path or http://127.0.0.1:PORT/path
  method: GET or HEAD only
  timeout_seconds: 1-30
  max_response_bytes: bounded
  expected_status: optional list

local_route_screenshot
  url: loopback URL only by default
  viewport: named desktop/tablet/mobile preset
  wait_until: load or network-idle with timeout
  artifact_label: optional safe label

local_accessibility_smoke
  url: loopback URL only by default
  viewport: named preset
  timeout_seconds: bounded
  artifact_label: optional safe label
```

All outputs should include structured fields for requested URL, resolved host,
policy source, elapsed milliseconds, status, warnings, artifact IDs or paths, and
redaction posture. They should not return raw page HTML, full response bodies,
cookies, storage values, authorization headers, or screenshot pixels inline.

## Test Matrix

Any implementation must cover:

- loopback URL allowed by default
- non-loopback URL requires approval or is blocked when approval is unavailable
- host allowlist matching is exact and scheme-aware
- timeout and cancellation record deterministic failure summaries
- redirect limits stop loops
- response previews are bounded and redacted
- screenshots are retained as artifacts rather than inline payloads
- accessibility reports are summarized with artifact pointers
- local dev server unavailable returns a structured diagnostic, not a crash
- replay capture records request fingerprints, policy decisions, summaries, and artifact references without storing private response bodies
- dashboard/static export smoke uses the FastAPI-served production path

## Non-Goals

The v8 network/browser diagnostic contract does not allow:

- general web browsing
- credentialed scraping
- remote exploitation or vulnerability scanning
- arbitrary browser scripting
- browser-native code editing
- form submission, checkout flows, posting content, or upload automation
- bypassing CORS, auth, robots, or application-level access controls
- using a browser as a hosted worker or remote control plane
- storing cookies, tokens, raw local storage, raw HTML, or private page content in portable exports

The first implementation should be useful for local app workflows and boring in
the best way: clear inputs, local-only defaults, structured evidence, hard
timeouts, and no surprise web agency.
