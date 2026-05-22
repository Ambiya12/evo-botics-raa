import {
  actionStatusTone,
  formatEnumLabel,
  severityTone,
} from "../../constants/adminLabels";
import type { EventLog } from "../../types/admin";
import { Panel } from "../ui/Panel";
import { StatusBadge } from "../ui/StatusBadge";

interface EventLogTableProps {
  logs: EventLog[];
}

export function EventLogTable({ logs }: EventLogTableProps) {
  return (
    <Panel
      className="panel--wide"
      eyebrow="Phase 2 logging"
      title="Recent events"
      action={<StatusBadge label={`${logs.length} events`} tone="muted" />}
      aria-label="Event logs"
    >
      {logs.length === 0 ? (
        <p className="panel-empty">No matching events. Clear the filter to see the full stream.</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Severity</th>
                <th>Source</th>
                <th>Message</th>
                <th>Session</th>
                <th>Action</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td>{log.timestamp}</td>
                  <td>
                    <StatusBadge label={log.severity} tone={severityTone[log.severity]} />
                  </td>
                  <td>{formatEnumLabel(log.source)}</td>
                  <td>{log.message}</td>
                  <td>{log.sessionId ?? "-"}</td>
                  <td className="table-code-cell">{log.action}</td>
                  <td>
                    <StatusBadge label={log.status} tone={actionStatusTone[log.status]} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Panel>
  );
}
