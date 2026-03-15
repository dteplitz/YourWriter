interface EmotionBarProps {
  name: string;
  value: number; // expected 0–1
  isChanged?: boolean;
}

export function EmotionBar({ name, value, isChanged }: EmotionBarProps) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className={`emotion-bar${isChanged ? ' emotion-bar--changed' : ''}`}>
      <span className="emotion-bar-label">{name}</span>
      <div className="emotion-bar-track">
        <div className="emotion-bar-fill" style={{ width: `${pct}%` }} />
      </div>
      <span className="emotion-bar-value">{pct}%</span>
    </div>
  );
}
