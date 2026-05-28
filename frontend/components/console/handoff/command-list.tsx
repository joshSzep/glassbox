import { DataList, DataListItem, DataListLabel, DataListMeta } from "@/components/ui/data-list";

export function CommandList({
  commands,
}: {
  commands: { display: string; purpose: string; read_only: boolean }[];
}) {
  if (commands.length === 0) {
    return null;
  }
  return (
    <DataList density="compact">
      {commands.slice(0, 6).map((command) => (
        <DataListItem key={command.display}>
          <DataListLabel className="break-all">{command.display}</DataListLabel>
          <DataListMeta>
            {command.purpose} {command.read_only ? "(read-only)" : "(explicit mutation)"}
          </DataListMeta>
        </DataListItem>
      ))}
    </DataList>
  );
}
