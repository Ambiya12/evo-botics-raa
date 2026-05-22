import type { ReactNode } from "react";

interface PanelProps {
  title: string;
  eyebrow?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  "aria-label"?: string;
}

export function Panel({
  title,
  eyebrow,
  action,
  children,
  className = "",
  "aria-label": ariaLabel,
}: PanelProps) {
  return (
    <section className={`panel ${className}`.trim()} aria-label={ariaLabel ?? title}>
      <div className="panel__header">
        <div>
          {eyebrow ? <p className="section-kicker">{eyebrow}</p> : null}
          <h3>{title}</h3>
        </div>
        {action ? <div className="panel__action">{action}</div> : null}
      </div>
      {children}
    </section>
  );
}
