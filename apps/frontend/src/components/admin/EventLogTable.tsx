import type { EventActionStatus, EventLog, Severity } from "../../types/admin";

function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "success" | "warning" | "danger" | "neutral" | "mock";
}) {
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}

function severityTone(severity: Severity): "neutral" | "warning" | "danger" {
  if (severity === "warning") {
    return "warning";
  }

  if (severity === "error" || severity === "critical") {
    return "danger";
  }

  return "neutral";
}

function actionStatusTone(status: EventActionStatus): "success" | "warning" | "danger" {
  if (status === "succeeded") {
    return "success";
  }

  if (status === "pending") {
    return "warning";
  }

  return "danger";
}

interface EventLogTableProps {
  logs: EventLog[];
}

export function EventLogTable({ logs }: EventLogTableProps) {
  return (
    <section className="panel panel--wide" aria-label="Event logs">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Phase 2 logging</p>
          <h3>Recent events</h3>
        </div>
        <StatusBadge label={`${logs.length} events`} />
      </div>

      {logs.length === 0 ? (
        <p className="panel-empty">No events yet. Logs will appear when robot and admin actions run.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Source</th>
                <th>Message</th>
                <th>Session ID</th>
                <th>Action</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.timestamp}</td>
                  <td>
                    <StatusBadge label={log.severity} tone={severityTone(log.severity)} />
                  </td>
                  <td>{log.source}</td>
                  <td>{log.message}</td>
                  <td>{log.sessionId ?? "-"}</td>
                  <td className="table-code-cell">{log.action}</td>
                  <td>
                    <StatusBadge label={log.status} tone={actionStatusTone(log.status)} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
