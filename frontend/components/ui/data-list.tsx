import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const dataListVariants = cva(
  "divide-y divide-border/70 rounded-md border border-border/80 bg-surface text-card-foreground",
  {
    variants: {
      density: {
        compact: "text-console",
        default: "text-sm",
      },
    },
    defaultVariants: {
      density: "default",
    },
  },
);

export interface DataListProps
  extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof dataListVariants> {}

const DataList = React.forwardRef<HTMLDivElement, DataListProps>(
  ({ className, density, ...props }, ref) => (
    <div
      className={cn(dataListVariants({ density }), className)}
      ref={ref}
      role="list"
      {...props}
    />
  ),
);
DataList.displayName = "DataList";

const DataListItem = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div
      className={cn(
        "grid min-h-density-row gap-1 px-3 py-2 transition-colors hover:bg-surface-raised",
        className,
      )}
      ref={ref}
      role="listitem"
      {...props}
    />
  ),
);
DataListItem.displayName = "DataListItem";

const DataListLabel = ({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) => (
  <span className={cn("font-medium text-foreground", className)} {...props} />
);
DataListLabel.displayName = "DataListLabel";

const DataListMeta = ({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) => (
  <span className={cn("text-xs text-muted-foreground", className)} {...props} />
);
DataListMeta.displayName = "DataListMeta";

export { DataList, DataListItem, DataListLabel, DataListMeta };
