import type {
  ConnectionStatus,
  EventActionStatus,
  IncidentStatus,
  RobotState,
  ServiceStatus,
  SessionFlowStep,
  Severity,
} from "../types/admin";
import type { BadgeTone } from "../components/ui/StatusBadge";

export const robotStateLabel: Record<RobotState, string> = {
  IDLE: "Idle",
  WAITING_FOR_QR: "Waiting for QR",
  VALIDATING_RESERVATION: "Validating reservation",
  GUIDING: "Guiding visitor",
  ARRIVED: "Arrived",
  RETURNING_HOME: "Returning home",
  ERROR: "Error",
  EMERGENCY_STOP: "Emergency stop",
};

export const flowStepLabel: Record<SessionFlowStep, string> = {
  WAITING_FOR_QR: "Waiting for QR",
  VALIDATING_RESERVATION: "Validating reservation",
  RESERVATION_VALID: "Reservation valid",
  BADGE_DISTRIBUTION: "Badge distribution",
  GUIDING: "Guiding",
  ARRIVED: "Arrived",
  RETURNING_HOME: "Returning home",
  ERROR: "Error",
};

export const connectionLabel: Record<ConnectionStatus, string> = {
  mock: "Mock mode",
  connecting: "Connecting...",
  connected_ros: "ROS connected",
  disconnected: "Disconnected",
  error: "Connection error",
};

export const serviceTone: Record<ServiceStatus, BadgeTone> = {
  online: "success",
  degraded: "warning",
  offline: "danger",
  mock: "muted",
};

export const connectionTone: Record<ConnectionStatus, BadgeTone> = {
  mock: "muted",
  connecting: "warning",
  connected_ros: "success",
  disconnected: "danger",
  error: "danger",
};

export const severityTone: Record<Severity, BadgeTone> = {
  info: "neutral",
  warning: "warning",
  error: "danger",
  critical: "danger",
};

export const actionStatusTone: Record<EventActionStatus, BadgeTone> = {
  pending: "warning",
  succeeded: "success",
  failed: "danger",
};

export const incidentStatusTone: Record<IncidentStatus, BadgeTone> = {
  open: "warning",
  acknowledged: "neutral",
  resolved: "success",
};

export function formatEnumLabel(value: string): string {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}
