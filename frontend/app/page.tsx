import { Activity, CircleAlert, GitBranch, RadioTower } from "lucide-react";

import { Button } from "@/components/ui/button";

const queues = [
  { label: "Approvals", count: 0, tone: "bg-amber-100 text-amber-900" },
  { label: "Questions", count: 0, tone: "bg-sky-100 text-sky-900" },
  { label: "Failures", count: 0, tone: "bg-red-100 text-red-900" },
  { label: "Active", count: 0, tone: "bg-emerald-100 text-emerald-900" },
];

export default function Home() {
  return (
    <main className="min-h-screen px-4 py-5 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="flex flex-col gap-3 border-b pb-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">Glassbox</p>
            <h1 className="text-2xl font-semibold tracking-normal">Operator Console</h1>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="inline-flex h-8 items-center gap-2 rounded-md border bg-card px-3 font-medium">
              <RadioTower className="h-4 w-4 text-emerald-700" aria-hidden="true" />
              historical snapshot
            </span>
            <Button variant="outline" size="sm">
              <Activity className="h-4 w-4" aria-hidden="true" />
              Refresh
            </Button>
          </div>
        </header>

        <section className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
          <aside className="flex flex-col gap-4">
            <div className="rounded-lg border bg-card p-4 shadow-sm">
              <div className="mb-3 flex items-center justify-between gap-3">
                <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
                  Workspace
                </h2>
                <span className="rounded-md bg-secondary px-2 py-1 text-xs font-medium text-secondary-foreground">
                  local
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {queues.map((queue) => (
                  <button
                    className="rounded-md border bg-background p-3 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    key={queue.label}
                    type="button"
                  >
                    <span className="block text-xs font-medium text-muted-foreground">
                      {queue.label}
                    </span>
                    <span className="mt-2 flex items-center justify-between gap-2 text-lg font-semibold">
                      {queue.count}
                      <span className={`rounded px-2 py-0.5 text-xs ${queue.tone}`}>clear</span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div className="rounded-lg border bg-card p-4 shadow-sm">
              <h2 className="mb-3 text-sm font-semibold uppercase tracking-normal text-muted-foreground">
                Queues
              </h2>
              <div className="space-y-2">
                {queues.map((queue) => (
                  <button
                    className="flex h-10 w-full items-center justify-between rounded-md px-3 text-sm font-medium hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    key={queue.label}
                    type="button"
                  >
                    <span>{queue.label}</span>
                    <span className="rounded bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                      {queue.count}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          </aside>

          <section className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="rounded-lg border bg-card shadow-sm">
              <div className="flex items-start justify-between gap-4 border-b p-4">
                <div>
                  <h2 className="text-lg font-semibold">No session selected</h2>
                  <p className="mt-1 text-sm text-muted-foreground">
                    Transcript, timeline, actions, and evidence are empty.
                  </p>
                </div>
                <span className="inline-flex h-8 items-center gap-2 rounded-md bg-muted px-3 text-sm font-medium text-muted-foreground">
                  <GitBranch className="h-4 w-4" aria-hidden="true" />
                  no branch
                </span>
              </div>
              <div className="grid min-h-[420px] place-items-center p-8 text-center">
                <div className="max-w-sm">
                  <CircleAlert
                    className="mx-auto h-8 w-8 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <p className="mt-4 text-sm font-medium">No operator action is selected.</p>
                  <p className="mt-2 text-sm text-muted-foreground">
                    Session context is waiting for an aggregate row or direct session link.
                  </p>
                </div>
              </div>
            </div>

            <aside className="rounded-lg border bg-card p-4 shadow-sm">
              <h2 className="text-sm font-semibold uppercase tracking-normal text-muted-foreground">
                Inspector
              </h2>
              <div className="mt-4 space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Stream</span>
                  <span className="font-medium">offline</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Projection</span>
                  <span className="font-medium">unknown</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Next action</span>
                  <span className="font-medium">none</span>
                </div>
              </div>
            </aside>
          </section>
        </section>
      </div>
    </main>
  );
}
