export const appQueues = [
  "all",
  "approvals",
  "questions",
  "failures",
  "degraded",
  "active",
  "action-needed",
  "historical",
] as const;

export type AppQueue = (typeof appQueues)[number];

export const inspectorTabs = [
  "overview",
  "transcript",
  "timeline",
  "actions",
  "lineage",
  "compare",
  "runtime",
  "evidence",
  "metrics",
  "events",
] as const;

export type InspectorTab = (typeof inspectorTabs)[number];

export const appSurfaces = ["sessions", "tasks", "memory", "repository"] as const;

export type AppSurface = (typeof appSurfaces)[number];

export const taskQueueFilters = [
  "all",
  "active",
  "blocked",
  "failed",
  "completed",
  "background",
  "historical",
] as const;

export type TaskQueueFilter = (typeof taskQueueFilters)[number];

export type AppRouteState = {
  compareSessionId: string | null;
  queue: AppQueue;
  selectedSessionId: string | null;
  selectedTaskId: string | null;
  surface: AppSurface;
  tab: InspectorTab;
  taskQueue: TaskQueueFilter;
};

export type AppRouteOptions = {
  basePath?: string;
};

type AppRouteBuildState = Omit<AppRouteState, "selectedTaskId" | "surface" | "taskQueue"> &
  Partial<Pick<AppRouteState, "selectedTaskId" | "surface" | "taskQueue">>;

const DEFAULT_BASE_PATH = "/app";
const queueSet = new Set<string>(appQueues);
const inspectorTabSet = new Set<string>(inspectorTabs);
const taskQueueSet = new Set<string>(taskQueueFilters);

export function createDefaultAppRoute(): AppRouteState {
  return {
    compareSessionId: null,
    queue: "all",
    selectedSessionId: null,
    selectedTaskId: null,
    surface: "sessions",
    tab: "overview",
    taskQueue: "active",
  };
}

export function parseAppRoute(input: string | URL, options: AppRouteOptions = {}): AppRouteState {
  const url = normalizeUrl(input);
  const basePath = normalizeBasePath(options.basePath);
  const segments = pathSegments(stripBasePath(url.pathname, basePath));
  const sessionFromQuery = emptyToNull(url.searchParams.get("session"));
  const queueFromQuery = parseQueue(url.searchParams.get("queue"));
  const tab = parseInspectorTab(url.searchParams.get("tab"));
  const compareSessionId = emptyToNull(url.searchParams.get("compare"));
  const taskQueue = parseTaskQueue(url.searchParams.get("taskQueue")) ?? "active";

  if (segments[0] === "tasks") {
    return {
      compareSessionId: null,
      queue: "all",
      selectedSessionId: null,
      selectedTaskId: segments[1] ? decodePathSegment(segments[1]) : null,
      surface: "tasks",
      tab: "overview",
      taskQueue,
    };
  }

  if (segments[0] === "memory") {
    return {
      compareSessionId: null,
      queue: "all",
      selectedSessionId: null,
      selectedTaskId: null,
      surface: "memory",
      tab: "overview",
      taskQueue,
    };
  }

  if (segments[0] === "repository-index") {
    return {
      compareSessionId: null,
      queue: "all",
      selectedSessionId: null,
      selectedTaskId: null,
      surface: "repository",
      tab: "overview",
      taskQueue,
    };
  }

  if (segments[0] === "sessions" && segments[1]) {
    return {
      compareSessionId,
      queue: queueFromQuery ?? "all",
      selectedSessionId: decodePathSegment(segments[1]),
      selectedTaskId: null,
      surface: "sessions",
      tab: compareSessionId !== null && tab === "overview" ? "compare" : tab,
      taskQueue,
    };
  }

  if (sessionFromQuery !== null) {
    return {
      compareSessionId,
      queue: queueFromQuery ?? "all",
      selectedSessionId: sessionFromQuery,
      selectedTaskId: null,
      surface: "sessions",
      tab: compareSessionId !== null && tab === "overview" ? "compare" : tab,
      taskQueue,
    };
  }

  if (segments[0] === "queues") {
    return {
      compareSessionId: null,
      queue: parseQueue(segments[1]) ?? "all",
      selectedSessionId: null,
      selectedTaskId: null,
      surface: "sessions",
      tab: "overview",
      taskQueue,
    };
  }

  return {
    compareSessionId: null,
    queue: queueFromQuery ?? "all",
    selectedSessionId: null,
    selectedTaskId: null,
    surface: "sessions",
    tab: "overview",
    taskQueue,
  };
}

export function buildAppRoute(state: AppRouteBuildState, options: AppRouteOptions = {}): string {
  const basePath = normalizeBasePath(options.basePath);
  const searchParams = new URLSearchParams();
  let pathname = basePath;
  const surface = state.surface ?? "sessions";
  const taskQueue = state.taskQueue ?? "active";
  const selectedTaskId = state.selectedTaskId ?? null;

  if (surface === "tasks") {
    pathname =
      selectedTaskId === null
        ? `${basePath}/tasks`
        : `${basePath}/tasks/${encodePathSegment(selectedTaskId)}`;
    if (taskQueue !== "active") {
      searchParams.set("taskQueue", taskQueue);
    }
  } else if (surface === "memory") {
    pathname = `${basePath}/memory`;
  } else if (surface === "repository") {
    pathname = `${basePath}/repository-index`;
  } else if (state.selectedSessionId !== null) {
    pathname = `${basePath}/sessions/${encodePathSegment(state.selectedSessionId)}`;
    if (state.queue !== "all") {
      searchParams.set("queue", state.queue);
    }
    if (state.compareSessionId !== null) {
      searchParams.set("compare", state.compareSessionId);
    }
    if (state.tab !== "overview") {
      searchParams.set("tab", state.tab);
    }
  } else if (state.queue !== "all") {
    pathname = `${basePath}/queues/${state.queue}`;
  }

  const query = searchParams.toString();
  return query ? `${pathname}?${query}` : pathname;
}

export function selectQueueRoute(route: AppRouteState, queue: AppQueue): AppRouteState {
  return {
    ...route,
    compareSessionId: null,
    queue,
    selectedSessionId: null,
    selectedTaskId: null,
    surface: "sessions",
    tab: "overview",
  };
}

export function selectSessionRoute(route: AppRouteState, sessionId: string): AppRouteState {
  return {
    ...route,
    compareSessionId: null,
    selectedSessionId: sessionId,
    selectedTaskId: null,
    surface: "sessions",
    tab: "overview",
  };
}

export function openLineageTargetRoute(route: AppRouteState, sessionId: string): AppRouteState {
  return selectSessionRoute(route, sessionId);
}

export function setCompareRoute(
  route: AppRouteState,
  compareSessionId: string | null,
): AppRouteState {
  return {
    ...route,
    compareSessionId,
    tab: compareSessionId === null ? route.tab : "compare",
  };
}

export function setInspectorTabRoute(route: AppRouteState, tab: InspectorTab): AppRouteState {
  return {
    ...route,
    tab,
  };
}

export function selectTaskQueueRoute(
  route: AppRouteState,
  taskQueue: TaskQueueFilter,
): AppRouteState {
  return {
    ...route,
    compareSessionId: null,
    selectedSessionId: null,
    selectedTaskId: null,
    surface: "tasks",
    tab: "overview",
    taskQueue,
  };
}

export function selectTaskRoute(route: AppRouteState, taskId: string): AppRouteState {
  return {
    ...route,
    compareSessionId: null,
    selectedSessionId: null,
    selectedTaskId: taskId,
    surface: "tasks",
    tab: "overview",
  };
}

export function selectKnowledgeRoute(
  route: AppRouteState,
  surface: Extract<AppSurface, "memory" | "repository">,
): AppRouteState {
  return {
    ...route,
    compareSessionId: null,
    selectedSessionId: null,
    selectedTaskId: null,
    surface,
    tab: "overview",
  };
}

export function recoverInvalidSessionRoute(route: AppRouteState): AppRouteState {
  return selectQueueRoute(route, route.queue);
}

function normalizeUrl(input: string | URL): URL {
  if (input instanceof URL) {
    return input;
  }
  return new URL(input, "http://glassbox.local");
}

function normalizeBasePath(basePath = DEFAULT_BASE_PATH): string {
  const trimmed = basePath.trim().replace(/\/+$/, "");
  if (trimmed.length === 0 || trimmed === "/") {
    return "";
  }
  return trimmed.startsWith("/") ? trimmed : `/${trimmed}`;
}

function stripBasePath(pathname: string, basePath: string): string {
  if (basePath === "") {
    return pathname;
  }
  if (pathname === basePath) {
    return "/";
  }
  if (pathname.startsWith(`${basePath}/`)) {
    return pathname.slice(basePath.length);
  }
  return pathname;
}

function pathSegments(pathname: string): string[] {
  return pathname
    .split("/")
    .map((segment) => segment.trim())
    .filter(Boolean);
}

function parseQueue(value: string | null | undefined): AppQueue | null {
  if (value === undefined || value === null) {
    return null;
  }
  return queueSet.has(value) ? (value as AppQueue) : null;
}

function parseInspectorTab(value: string | null | undefined): InspectorTab {
  if (value === undefined || value === null) {
    return "overview";
  }
  return inspectorTabSet.has(value) ? (value as InspectorTab) : "overview";
}

function parseTaskQueue(value: string | null | undefined): TaskQueueFilter | null {
  if (value === undefined || value === null) {
    return null;
  }
  return taskQueueSet.has(value) ? (value as TaskQueueFilter) : null;
}

function emptyToNull(value: string | null): string | null {
  return value === null || value.trim().length === 0 ? null : value;
}

function encodePathSegment(value: string): string {
  return encodeURIComponent(value);
}

function decodePathSegment(value: string): string {
  return decodeURIComponent(value);
}
