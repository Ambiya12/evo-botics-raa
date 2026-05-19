import { BatteryCharging, Clock3, MapPin, Radio, Route, Signal } from "lucide-react";
import type { ConnectionStatus, RobotStatus } from "../../types/admin";

const robotStateLabel: Record<RobotStatus["state"], string> = {
  IDLE: "Idle",
  WAITING_FOR_QR: "Waiting for QR",
  VALIDATING_RESERVATION: "Validating reservation",
  GUIDING: "Guiding",
  ARRIVED: "Arrived",
  RETURNING_HOME: "Returning home",
  ERROR: "Error",
  EMERGENCY_STOP: "Emergency stop",
};

const connectionLabel: Record<ConnectionStatus, string> = {
  mock: "Mock",
  disconnected: "Disconnected",
  connected_ros: "Connected to ROS",
};

const connectionTone: Record<ConnectionStatus, "mock" | "danger" | "success"> = {
  mock: "mock",
  disconnected: "danger",
  connected_ros: "success",
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

interface RobotStatusOverviewProps {
  robotStatus: RobotStatus;
}

export function RobotStatusOverview({ robotStatus }: RobotStatusOverviewProps) {
  const cards = [
    {
      label: "Robot status",
      value: robotStateLabel[robotStatus.state],
      meta: `Robot ID: ${robotStatus.id}`,
      icon: Signal,
      tone: "mock" as const,
    },
    {
      label: "Battery",
      value: `${robotStatus.battery}%`,
      meta: robotStatus.battery < 25 ? "Battery is low" : "Battery level stable",
      icon: BatteryCharging,
      tone: robotStatus.battery < 25 ? ("warning" as const) : ("success" as const),
    },
    {
      label: "Position / waypoint",
      value: robotStatus.location,
      meta: `Waypoint: ${robotStatus.currentWaypoint}`,
      icon: MapPin,
      tone: "neutral" as const,
    },
    {
      label: "Current mission",
      value: robotStatus.currentMissionSessionId ?? "No active session",
      meta: `Destination: ${robotStatus.destination}`,
      icon: Route,
      tone: "neutral" as const,
    },
    {
      label: "Last incident",
      value: robotStatus.lastIncidentSummary,
      meta: "Incident stream from monitoring",
      icon: Radio,
      tone: "warning" as const,
    },
    {
      label: "Last update",
      value: robotStatus.lastUpdate,
      meta: "Timestamp from status provider",
      icon: Clock3,
      tone: "neutral" as const,
    },
  ];

  return (
    <section className="panel panel--overview" aria-label="Robot status overview">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Dashboard home</p>
          <h3>Robot status overview</h3>
        </div>
        <StatusBadge
          label={connectionLabel[robotStatus.connectionStatus]}
          tone={connectionTone[robotStatus.connectionStatus]}
        />
      </div>

      <div className="overview-grid overview-grid--panel">
        {cards.map((card) => (
          <article className="metric-card" key={card.label}>
            <div className={`metric-card__icon metric-card__icon--${card.tone}`}>
              <card.icon aria-hidden="true" size={21} />
            </div>
            <div>
              <p>{card.label}</p>
              <strong>{card.value}</strong>
              <span>{card.meta}</span>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
