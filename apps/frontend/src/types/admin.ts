import type { LucideIcon } from "lucide-react";

export type RobotState =
  | "IDLE"
  | "WAITING_FOR_QR"
  | "VALIDATING_RESERVATION"
  | "GUIDING"
  | "ARRIVED"
  | "RETURNING_HOME"
  | "ERROR"
  | "EMERGENCY_STOP";

export type ServiceStatus = "online" | "degraded" | "offline" | "mock";

export type ConnectionStatus = "mock" | "disconnected" | "connected_ros";

export type Severity = "info" | "warning" | "error" | "critical";

export type IncidentStatus = "open" | "acknowledged" | "resolved";

export interface RobotStatus {
  id: string;
  name: string;
  mode: "mock" | "rosbridge";
  connectionStatus: ConnectionStatus;
  state: RobotState;
  battery: number;
  location: string;
  currentWaypoint: string;
  destination: string;
  currentMissionSessionId: string | null;
  lastIncidentSummary: string;
  lastUpdate: string;
  emergencyStop: boolean;
  services: Array<{
    name: string;
    status: ServiceStatus;
    detail: string;
  }>;
}

export interface VisitorSession {
  id: string;
  visitorName: string;
  company: string;
  host: string;
  room: string;
  step: RobotState;
  startedAt: string;
  reservationStatus: "valid" | "invalid" | "expired" | "pending";
}

export interface EventLog {
  id: string;
  timestamp: string;
  source: string;
  severity: Severity;
  message: string;
  sessionId?: string;
}

export interface Incident {
  id: string;
  title: string;
  status: IncidentStatus;
  severity: Exclude<Severity, "info">;
  timestamp: string;
  description: string;
}

export interface NavigationItem {
  label: string;
  icon: LucideIcon;
  active?: boolean;
}
