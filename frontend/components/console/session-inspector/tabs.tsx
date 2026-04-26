import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { buildAppRoute, type AppQueue, type InspectorTab } from "@/routing/app-route";
import type { DashboardState } from "@/state/session-state";

const inspectorTabs: { label: string; value: InspectorTab }[] = [
  { label: "Overview", value: "overview" },
  { label: "Transcript", value: "transcript" },
  { label: "Timeline", value: "timeline" },
  { label: "Actions", value: "actions" },
  { label: "Lineage", value: "lineage" },
  { label: "Compare", value: "compare" },
  { label: "Runtime", value: "runtime" },
  { label: "Evidence", value: "evidence" },
  { label: "Metrics", value: "metrics" },
  { label: "Events", value: "events" },
];

export function InspectorTabs({
  activeTab,
  data,
  onSelectTab,
  queue,
}: {
  activeTab: InspectorTab;
  data: DashboardState;
  onSelectTab?: (tab: InspectorTab) => void;
  queue: AppQueue;
}) {
  return (
    <div className="overflow-x-auto border-b p-3">
      <Tabs value={activeTab}>
        <TabsList aria-label="Inspector tabs">
          {inspectorTabs.map((tab) => (
            <TabsTrigger asChild key={tab.value} value={tab.value}>
              <a
                href={buildAppRoute({
                  compareSessionId: data.compareSessionId,
                  queue,
                  selectedSessionId: data.sessionId,
                  tab: tab.value,
                })}
                onClick={(event) => {
                  if (onSelectTab === undefined) {
                    return;
                  }
                  event.preventDefault();
                  onSelectTab(tab.value);
                }}
              >
                {tab.label}
              </a>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
    </div>
  );
}
