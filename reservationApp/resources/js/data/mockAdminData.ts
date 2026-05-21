import {
  Activity,
  Bell,
  ClipboardList,
  Gauge,
  Map,
  Settings,
  ShieldAlert,
} from "lucide-react";
import type {
  ArmJoint,
  EventLog,
  Incident,
  JetsonMetrics,
  NavigationItem,
  RobotStatus,
  VisitorSession,
} from "../types/admin";

export const navigationItems: NavigationItem[] = [
  { id: "overview", label: "Overview", icon: Gauge },
  { id: "live-status", label: "Live status", icon: Activity },
  { id: "sessions", label: "Sessions", icon: ClipboardList },
  { id: "incidents", label: "Incidents", icon: Bell },
  { id: "map", label: "Map", icon: Map },
  { id: "safety", label: "Safety", icon: ShieldAlert },
  { id: "settings", label: "Settings", icon: Settings },
];

export const robotStatus: RobotStatus = {
  id: "evo-botics-01",
  name: "Evo-Botics Reception Robot",
  mode: "mock",
  connectionStatus: "mock",
  state: "GUIDING",
  battery: 76,
  location: "Reception",
  currentWaypoint: "hallway-east",
  destination: "Meeting Room A",
  currentMissionSessionId: "SES-2026-014",
  lastIncidentSummary: "Battery monitoring warning acknowledged",
  lastUpdate: "14:32:18",
  emergencyStop: false,
  services: [
    {
      name: "Navigation",
      status: "mock",
      detail: "Nav2 bridge placeholder",
    },
    {
      name: "Reservation API",
      status: "online",
      detail: "Mock validation under 3s",
    },
    {
      name: "QR scanner",
      status: "mock",
      detail: "Awaiting camera integration",
    },
    {
      name: "Notifications",
      status: "online",
      detail: "Webhook pipeline ready",
    },
  ],
};

export const currentSession: VisitorSession = {
  id: "SES-2026-014",
  visitorName: "Maya Chen",
  company: "Novea Labs",
  host: "Jules Bourrin",
  room: "Meeting Room A",
  reservationId: "RES-2026-118",
  reservationStatus: "valid",
  checkInTime: "14:28",
  flowStep: "GUIDING",
  statusMessage: "Visitor is being guided to Meeting Room A",
  flowError: null,
  updatedAt: "14:32:18",
};

export const eventLogs: EventLog[] = [
  {
    id: "LOG-001",
    timestamp: "14:32:18",
    source: "navigation",
    severity: "info",
    message: "Guidance mission active toward Meeting Room A.",
    sessionId: "SES-2026-014",
    action: "start_guidance",
    status: "succeeded",
  },
  {
    id: "LOG-002",
    timestamp: "14:31:02",
    source: "reservation_api",
    severity: "info",
    message: "Reservation RES-2026-118 validated in 842ms.",
    sessionId: "SES-2026-014",
    action: "validate_reservation",
    status: "succeeded",
  },
  {
    id: "LOG-003",
    timestamp: "14:30:46",
    source: "qr_scanner",
    severity: "info",
    message: "QR payload received from mock scanner.",
    sessionId: "SES-2026-014",
    action: "scan_qr",
    status: "succeeded",
  },
  {
    id: "LOG-004",
    timestamp: "14:22:11",
    source: "battery",
    severity: "warning",
    message: "Battery below 80%; continue monitoring before demo run.",
    sessionId: null,
    action: "monitor_battery",
    status: "pending",
  },
  {
    id: "LOG-005",
    timestamp: "14:18:27",
    source: "notification",
    severity: "info",
    message: "Staff notification sent for low battery warning.",
    sessionId: null,
    action: "notify_staff",
    status: "succeeded",
  },
  {
    id: "LOG-006",
    timestamp: "13:54:09",
    source: "reservation_api",
    severity: "error",
    message: "Reservation API timeout while validating RES-2026-103.",
    sessionId: "SES-2026-011",
    action: "validate_reservation",
    status: "failed",
  },
];

export const incidents: Incident[] = [
  {
    id: "INC-023",
    title: "Robot blocked in hallway",
    status: "open",
    severity: "critical",
    timestamp: "14:33",
    description: "Obstacle persisted for over 20s while robot was guiding a visitor.",
    relatedSessionId: "SES-2026-014",
  },
  {
    id: "INC-022",
    title: "Invalid reservation detected",
    status: "open",
    severity: "warning",
    timestamp: "14:29",
    description: "QR payload did not match a valid reservation in the current time window.",
    relatedSessionId: "SES-2026-013",
  },
  {
    id: "INC-021",
    title: "Battery monitoring warning",
    status: "acknowledged",
    severity: "warning",
    timestamp: "14:22",
    description: "Battery dropped below the preferred demo threshold.",
    relatedSessionId: null,
  },
  {
    id: "INC-020",
    title: "Reservation API timeout",
    status: "resolved",
    severity: "error",
    timestamp: "13:54",
    description: "Mock API exceeded the 3s validation target during test.",
    relatedSessionId: "SES-2026-011",
  },
];

export const armJoints: ArmJoint[] = [
  { name: "shoulder_pan",   position:  0.42, velocity: 0.0, effort:  1.2 },
  { name: "shoulder_lift",  position: -1.05, velocity: 0.0, effort:  3.8 },
  { name: "elbow",          position:  1.57, velocity: 0.0, effort:  2.1 },
  { name: "wrist_1",        position: -0.78, velocity: 0.0, effort:  0.7 },
  { name: "wrist_2",        position:  0.00, velocity: 0.0, effort:  0.4 },
  { name: "wrist_3",        position:  1.05, velocity: 0.0, effort:  0.3 },
];

export const jetsonMetrics: JetsonMetrics = {
  cpuPercent:      34,
  ramPercent:      58,
  gpuTempCelsius:  42,
  cpuTempCelsius:  38,
};
