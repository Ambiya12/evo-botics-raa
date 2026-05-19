import { AlertCircle, CheckCircle2, MapPin, UserRound } from "lucide-react";
import type { SessionFlowStep, VisitorSession } from "../../types/admin";

const flowStepLabel: Record<SessionFlowStep, string> = {
  WAITING_FOR_QR: "Waiting for QR",
  VALIDATING_RESERVATION: "Validating reservation",
  RESERVATION_VALID: "Reservation valid",
  BADGE_DISTRIBUTION: "Badge distribution",
  GUIDING: "Guiding",
  ARRIVED: "Arrived",
  RETURNING_HOME: "Returning home",
  ERROR: "Error",
};

function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "success" | "warning" | "danger" | "neutral" | "mock";
}) {
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}

function reservationTone(status: VisitorSession["reservationStatus"]): "success" | "warning" | "danger" {
  if (status === "valid") {
    return "success";
  }

  if (status === "pending") {
    return "warning";
  }

  return "danger";
}

interface CurrentVisitorSessionPanelProps {
  session: VisitorSession | null;
}

export function CurrentVisitorSessionPanel({ session }: CurrentVisitorSessionPanelProps) {
  if (!session) {
    return (
      <section className="panel session-panel" aria-label="Current visitor session">
        <div className="panel__header">
          <div>
            <p className="section-kicker">Current session</p>
            <h3>No active visitor session</h3>
          </div>
          <StatusBadge label="Idle" tone="neutral" />
        </div>
        <p className="panel-empty">The robot is waiting for the next visitor check-in.</p>
      </section>
    );
  }

  return (
    <section className="panel session-panel" aria-label="Current visitor session">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Current session</p>
          <h3>{session.id}</h3>
        </div>
        <StatusBadge
          label={session.reservationStatus}
          tone={reservationTone(session.reservationStatus)}
        />
      </div>

      <div className="session-hero">
        <div>
          <strong>{session.visitorName}</strong>
          <span>{session.company}</span>
        </div>
        <div className="session-hero__room">
          <MapPin aria-hidden="true" size={18} />
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
    </section>
  );
}
