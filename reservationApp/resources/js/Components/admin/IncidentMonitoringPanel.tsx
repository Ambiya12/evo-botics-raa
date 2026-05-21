import { AlertTriangle } from "lucide-react";
import {
  incidentStatusTone,
  severityTone,
} from "../../constants/adminLabels";
import type { Incident } from "../../types/admin";
import { Panel } from "../ui/Panel";
import { StatusBadge } from "../ui/StatusBadge";

interface IncidentMonitoringPanelProps {
  incidents: Incident[];
  onAcknowledge: (incidentId: string) => Promise<void>;
}

export function IncidentMonitoringPanel({
  incidents,
  onAcknowledge,
}: IncidentMonitoringPanelProps) {
  return (
    <Panel
      eyebrow="Staff exceptions"
      title="Incident monitoring"
      action={<AlertTriangle aria-hidden="true" size={19} strokeWidth={1.8} />}
      aria-label="Incident monitoring panel"
    >
      {incidents.length === 0 ? (
        <p className="panel-empty">No matching incidents.</p>
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
                    <span>Session {incident.relatedSessionId ?? "-"}</span>
                  </div>
                </div>

                <div className="incident-actions">
                  <StatusBadge label={incident.severity} tone={severityTone[incident.severity]} />
                  <StatusBadge
                    label={incident.status}
                    tone={incidentStatusTone[incident.status]}
                  />
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
    </Panel>
  );
}
