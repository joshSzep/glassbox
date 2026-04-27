import type { ReactNode } from "react";

export function SectionHeader({
  detail,
  icon,
  title,
}: {
  detail: string;
  icon: ReactNode;
  title: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-2 text-sm font-medium">
        {icon}
        {title}
      </div>
      <p className="mt-1 text-sm text-muted-foreground">{detail}</p>
    </div>
  );
}
