import { memo } from "react";

export type BadgeTone = "success" | "warning" | "danger" | "neutral" | "muted";

interface StatusBadgeProps {
  label: string;
  tone?: BadgeTone;
}

export const StatusBadge = memo(function StatusBadge({
  label,
  tone = "neutral",
}: StatusBadgeProps) {
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
});
