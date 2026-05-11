import { ClipboardList } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { operatorIconSizeClass } from "@/design-system/operator-status";

import { StateLine } from "./shared";
import type { RepositoryInspectorState } from "./types";

export function CommandRecipeBrowser({ repository }: { repository: RepositoryInspectorState }) {
  return (
    <section
      aria-label="Repository command recipes"
      className="min-w-0 rounded-md border border-border/80 bg-card p-4 shadow-sm"
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-normal">Command Recipes</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Advisory commands with source, confidence, and policy risk.
          </p>
        </div>
        <Badge variant="outline">{repository.commandRecipes.length}</Badge>
      </div>
      {repository.commandRecipes.length === 0 ? (
        <StateLine
          className="mt-3"
          icon={<ClipboardList className={operatorIconSizeClass} aria-hidden="true" />}
          value="No command recipes are available."
        />
      ) : (
        <Table className="mt-3">
          <TableHeader>
            <TableRow>
              <TableHead>Recipe</TableHead>
              <TableHead>Risk</TableHead>
              <TableHead>Command</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {repository.commandRecipes.slice(0, 8).map((recipe) => (
              <TableRow key={recipe.recipe_id}>
                <TableCell>
                  <p className="font-medium">{recipe.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {recipe.purpose} · {recipe.confidence}
                  </p>
                </TableCell>
                <TableCell>
                  <Badge variant={recipe.risk === "read_only" ? "outline" : "warning"}>
                    {recipe.risk}
                  </Badge>
                </TableCell>
                <TableCell className="break-all text-xs text-muted-foreground">
                  {recipe.command}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
