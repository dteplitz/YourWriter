interface ConstraintCardProps {
  name: string;
  value: unknown;
  isChanged?: boolean;
}

export function ConstraintCard({ name, value, isChanged }: ConstraintCardProps) {
  return (
    <div className={`constraint-card${isChanged ? ' constraint-card--changed' : ''}`}>
      <span className="constraint-card-key">{name}</span>
      <span className="constraint-card-value">{String(value)}</span>
    </div>
  );
}
