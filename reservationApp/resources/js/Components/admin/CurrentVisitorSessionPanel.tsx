import { AlertCircle, CheckCircle2, MapPin, UserRound } from "lucide-react";
import { flowStepLabel } from "../../constants/adminLabels";
import type { VisitorSession } from "../../types/admin";
import { Panel } from "../ui/Panel";
import { StatusBadge, type BadgeTone } from "../ui/StatusBadge";

interface CurrentVisitorSessionPanelProps {
  session: VisitorSession | null;
}

function reservationTone(status: VisitorSession["reservationStatus"]): BadgeTone {
  if (status === "valid") {
    return "success";
  }

  if (status === "pending") {
    return "warning";
  }

  return "danger";
}

export function CurrentVisitorSessionPanel({ session }: CurrentVisitorSessionPanelProps) {
  if (!session) {
    return (
      <Panel
        className="session-panel"
        eyebrow="Current session"
        title="No active visitor session"
        action={<StatusBadge label="Idle" tone="neutral" />}
        aria-label="Current visitor session"
      >
        <p className="panel-empty">The robot is waiting for the next visitor check-in.</p>
      </Panel>
    );
  }

  return (
    <Panel
      className="session-panel"
      eyebrow="Current session"
      title={session.id}
      action={
        <StatusBadge
          label={session.reservationStatus}
          tone={reservationTone(session.reservationStatus)}
        />
      }
      aria-label="Current visitor session"
    >
      <div className="session-hero">
        <div>
          <strong>{session.visitorName}</strong>
          <span>{session.company}</span>
        </div>
        <div className="session-hero__room">
          <MapPin aria-hidden="true" size={17} />
          {session.room}
        </div>
      </div>

      <div className="session-status-line">
        <CheckCircle2 aria-hidden="true" size={16} />
        <span>{session.statusMessage}</span>
      </div>

      {session.flowError ? (
        <div className="session-error-line" role="alert">
          <AlertCircle aria-hidden="true" size={16} />
          <span>{session.flowError}</span>
        </div>
      ) : null}

      <dl className="detail-list">
        <div>
          <dt>Host</dt>
          <dd>{session.host}</dd>
        </div>
        <div>
          <dt>Check-in</dt>
          <dd>{session.checkInTime}</dd>
        </div>
        <div>
          <dt>Flow step</dt>
          <dd>{flowStepLabel[session.flowStep]}</dd>
        </div>
        <div>
          <dt>Reservation</dt>
          <dd>{session.reservationId}</dd>
        </div>
        <div>
          <dt>Updated</dt>
          <dd>{session.updatedAt}</dd>
        </div>
        <div>
          <dt>Visitor</dt>
          <dd className="session-inline-value">
            <UserRound aria-hidden="true" size={14} />
            {session.visitorName}
          </dd>
        </div>
      </dl>
    </Panel>
  );
}
