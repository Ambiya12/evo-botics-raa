import type { LucideIcon } from "lucide-react";
import { memo } from "react";

interface MetricCardProps {
  label: string;
  value: string;
  meta: string;
  icon: LucideIcon;
  tone?: "neutral" | "success" | "warning" | "danger" | "muted";
}

export const MetricCard = memo(function MetricCard({
  label,
  value,
  meta,
  icon: Icon,
  tone = "neutral",
}: MetricCardProps) {
  return (
    <article className="metric-card">
      <div className={`metric-card__icon metric-card__icon--${tone}`}>
        <Icon aria-hidden="true" size={20} strokeWidth={1.8} />
      </div>
      <div className="metric-card__body">
        <p>{label}</p>
        <strong>{value}</strong>
        <span>{meta}</span>
      </div>
    </article>
  );
});
