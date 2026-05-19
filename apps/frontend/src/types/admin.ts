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

export type EventSource =
  | "reservation_api"
  | "navigation"
  | "qr_scanner"
  | "admin"
  | "notification"
  | "battery";

export type EventActionStatus = "pending" | "succeeded" | "failed";

export type IncidentStatus = "open" | "acknowledged" | "resolved";

export type SessionFlowStep =
  | "WAITING_FOR_QR"
  | "VALIDATING_RESERVATION"
  | "RESERVATION_VALID"
  | "BADGE_DISTRIBUTION"
  | "GUIDING"
  | "ARRIVED"
  | "RETURNING_HOME"
  | "ERROR";

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
  reservationId: string;
  reservationStatus: "valid" | "invalid" | "expired" | "pending";
  checkInTime: string;
  flowStep: SessionFlowStep;
  statusMessage: string;
  flowError: string | null;
  updatedAt: string;
}

export interface EventLog {
  id: string;
  timestamp: string;
  source: EventSource;
  severity: Severity;
  message: string;
  sessionId: string | null;
  action: string;
  status: EventActionStatus;
}

export interface Incident {
  id: string;
  title: string;
  status: IncidentStatus;
  severity: Exclude<Severity, "info">;
  timestamp: string;
  description: string;
  relatedSessionId: string | null;
}

export interface NavigationItem {
  label: string;
  icon: LucideIcon;
  active?: boolean;
}
