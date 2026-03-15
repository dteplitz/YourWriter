interface TraitBadgeProps {
  name: string;
  value: unknown;
  isChanged?: boolean;
}

function numericTier(value: number): string {
  if (value >= 0.85) return 'max';
  if (value >= 0.6) return 'high';
  if (value >= 0.3) return 'medium';
  return 'low';
}

export function TraitBadge({ name, value, isChanged }: TraitBadgeProps) {
  const isNumeric = typeof value === 'number';
  const tier = isNumeric ? numericTier(value as number) : 'text';
  const label = isNumeric
    ? `${name}: ${Math.round((value as number) * 100)}%`
    : `${name}: ${String(value)}`;

  return (
    <span
      className={`trait-badge trait-badge--${tier}${isChanged ? ' trait-badge--changed' : ''}`}
      title={isNumeric ? `${name}: ${(value as number).toFixed(2)}` : undefined}
    >
      {label}
    </span>
  );
}
