export function NonClaims({ claims }: { claims: string[] }) {
  if (claims.length === 0) {
    return null;
  }
  return (
    <ul className="grid gap-1 text-console text-muted-foreground">
      {claims.slice(0, 4).map((claim) => (
        <li key={claim}>{claim}</li>
      ))}
    </ul>
  );
}
