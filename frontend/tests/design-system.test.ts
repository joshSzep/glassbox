import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Badge, badgeVariants } from "../components/ui/badge";
import { Button, buttonVariants } from "../components/ui/button";
import { DataList, DataListItem, DataListLabel, DataListMeta } from "../components/ui/data-list";
import { Input } from "../components/ui/input";
import { Separator } from "../components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../components/ui/tabs";
import { Textarea } from "../components/ui/textarea";
import { operatorStatusTokens } from "../design-system/operator-status";

describe("design system primitives", () => {
  it("renders common form, status, tab, table, and list primitives", () => {
    const markup = renderToStaticMarkup(
      React.createElement(
        "section",
        null,
        React.createElement(Button, { type: "button", variant: "outline" }, "Refresh"),
        React.createElement(Input, { "aria-label": "Filter sessions" }),
        React.createElement(Textarea, { "aria-label": "Prompt" }),
        React.createElement(Badge, { variant: "warning" }, "Action"),
        React.createElement(Separator),
        React.createElement(
          Tabs,
          { defaultValue: "overview" },
          React.createElement(
            TabsList,
            { "aria-label": "Inspector tabs" },
            React.createElement(TabsTrigger, { value: "overview" }, "Overview"),
          ),
          React.createElement(TabsContent, { value: "overview" }, "Overview pane"),
        ),
        React.createElement(
          Table,
          null,
          React.createElement(
            TableHeader,
            null,
            React.createElement(TableRow, null, React.createElement(TableHead, null, "Session")),
          ),
          React.createElement(
            TableBody,
            null,
            React.createElement(TableRow, null, React.createElement(TableCell, null, "session-1")),
          ),
        ),
        React.createElement(
          DataList,
          { density: "compact" },
          React.createElement(
            DataListItem,
            null,
            React.createElement(DataListLabel, null, "Runtime"),
            React.createElement(DataListMeta, null, "healthy"),
          ),
        ),
      ),
    );

    expect(markup).toContain("Refresh");
    expect(markup).toContain("Action");
    expect(markup).toContain("session-1");
    expect(markup).toContain("Runtime");
  });

  it("keeps focus visibility and stable status sizing in shared variants", () => {
    expect(buttonVariants()).toContain("focus-visible:ring-2");
    expect(buttonVariants({ size: "icon" })).toContain("w-9");
    expect(badgeVariants({ variant: "success" })).toContain("min-w-status-chip");
  });

  it("defines operator status tokens with lucide-compatible icons", () => {
    expect(operatorStatusTokens.active.label).toBe("Active");
    expect(operatorStatusTokens.failed.badgeVariant).toBe("destructive");
    expect(
      renderToStaticMarkup(
        React.createElement(operatorStatusTokens.question.icon, { className: "h-4 w-4" }),
      ),
    ).toContain("svg");
  });
});
