import { AlertTriangle } from "lucide-react";
import type { Incident, IncidentStatus } from "../../types/admin";

function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "success" | "warning" | "danger" | "neutral" | "mock";
}) {
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}

function statusTone(status: IncidentStatus): "warning" | "success" | "neutral" {
  if (status === "open") {
    return "warning";
  }

  if (status === "resolved") {
    return "success";
  }

  return "neutral";
}

function severityTone(severity: Incident["severity"]): "warning" | "danger" {
  if (severity === "warning") {
    return "warning";
  }

  return "danger";
}

interface IncidentMonitoringPanelProps {
  incidents: Incident[];
  onAcknowledge: (incidentId: string) => Promise<void>;
}

export function IncidentMonitoringPanel({
  incidents,
  onAcknowledge,
}: IncidentMonitoringPanelProps) {
  return (
    <section className="panel" aria-label="Incident monitoring panel">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Staff exceptions</p>
          <h3>Incident monitoring</h3>
        </div>
        <AlertTriangle aria-hidden="true" size={20} />
      </div>

      {incidents.length === 0 ? (
        <p className="panel-empty">No incidents detected.</p>
      ) : (
        <div className="incident-list">
          {incidents.map((incident) => {
            const canAcknowledge = incident.status === "open";

            return (
              <article className="incident-item" key={incident.id}>
                <div>
                  <strong>{incident.title}</strong>
                  <p>{incident.description}</p>
                  <div className="incident-meta">
                    <span>{incident.timestamp}</span>
                    <span>Session: {incident.relatedSessionId ?? "-"}</span>
                  </div>
                </div>

                <div className="incident-actions">
                  <StatusBadge label={incident.severity} tone={severityTone(incident.severity)} />
                  <StatusBadge label={incident.status} tone={statusTone(incident.status)} />
                  <button
                    className="incident-ack-button"
                    type="button"
                    disabled={!canAcknowledge}
                    onClick={() => void onAcknowledge(incident.id)}
                  >
                    Acknowledge
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
