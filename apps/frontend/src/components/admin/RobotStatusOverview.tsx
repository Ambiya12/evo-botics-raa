import { BatteryCharging, Clock3, MapPin, Radio, Route, Signal } from "lucide-react";
import {
  connectionLabel,
  connectionTone,
  robotStateLabel,
} from "../../constants/adminLabels";
import type { RobotStatus } from "../../types/admin";
import { MetricCard } from "../ui/MetricCard";
import { Panel } from "../ui/Panel";
import { StatusBadge } from "../ui/StatusBadge";

interface RobotStatusOverviewProps {
  robotStatus: RobotStatus;
}

export function RobotStatusOverview({ robotStatus }: RobotStatusOverviewProps) {
  const metrics = [
    {
      label: "Robot status",
      value: robotStateLabel[robotStatus.state],
      meta: robotStatus.id,
      icon: Signal,
      tone: robotStatus.emergencyStop ? ("danger" as const) : ("neutral" as const),
    },
    {
      label: "Battery",
      value: `${robotStatus.battery}%`,
      meta: robotStatus.battery < 25 ? "Low battery" : "Stable reserve",
      icon: BatteryCharging,
      tone: robotStatus.battery < 25 ? ("warning" as const) : ("success" as const),
    },
    {
      label: "Position",
      value: robotStatus.location,
      meta: `Waypoint ${robotStatus.currentWaypoint}`,
      icon: MapPin,
      tone: "neutral" as const,
    },
    {
      label: "Mission",
      value: robotStatus.currentMissionSessionId ?? "No session",
      meta: robotStatus.destination,
      icon: Route,
      tone: "neutral" as const,
    },
    {
      label: "Last incident",
      value: robotStatus.lastIncidentSummary,
      meta: "Monitoring stream",
      icon: Radio,
      tone: "warning" as const,
    },
    {
      label: "Last update",
      value: robotStatus.lastUpdate,
      meta: "Status provider",
      icon: Clock3,
      tone: "muted" as const,
    },
  ];

  return (
    <Panel
      className="panel--overview"
      eyebrow="Dashboard home"
      title="Robot status overview"
      action={
        <StatusBadge
          label={connectionLabel[robotStatus.connectionStatus]}
          tone={connectionTone[robotStatus.connectionStatus]}
        />
      }
    >
      <div className="overview-grid">
        {metrics.map((metric) => (
          <MetricCard {...metric} key={metric.label} />
        ))}
      </div>
    </Panel>
  );
}
