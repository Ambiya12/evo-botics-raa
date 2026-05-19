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
  EventLog,
  Incident,
  NavigationItem,
  RobotStatus,
  VisitorSession,
} from "../types/admin";

export const navigationItems: NavigationItem[] = [
  { label: "Overview", icon: Gauge, active: true },
  { label: "Live status", icon: Activity },
  { label: "Sessions", icon: ClipboardList },
  { label: "Incidents", icon: Bell },
  { label: "Map", icon: Map },
  { label: "Safety", icon: ShieldAlert },
  { label: "Settings", icon: Settings },
];

export const robotStatus: RobotStatus = {
  id: "evo-botics-01",
  name: "Evo-Botics Reception Robot",
  mode: "mock",
  state: "GUIDING",
  battery: 76,
  location: "Reception",
  currentWaypoint: "hallway-east",
  destination: "Meeting Room A",
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
  step: "GUIDING",
  startedAt: "14:28",
  reservationStatus: "valid",
};

export const eventLogs: EventLog[] = [
  {
    id: "LOG-001",
    timestamp: "14:32:18",
    source: "navigation",
    severity: "info",
    message: "Guidance mission active toward Meeting Room A.",
    sessionId: "SES-2026-014",
  },
  {
    id: "LOG-002",
    timestamp: "14:31:02",
    source: "reservation_api",
    severity: "info",
    message: "Reservation RES-2026-118 validated in 842ms.",
    sessionId: "SES-2026-014",
  },
  {
    id: "LOG-003",
    timestamp: "14:30:46",
    source: "qr_scanner",
    severity: "info",
    message: "QR payload received from mock scanner.",
    sessionId: "SES-2026-014",
  },
  {
    id: "LOG-004",
    timestamp: "14:22:11",
    source: "battery",
    severity: "warning",
    message: "Battery below 80%; continue monitoring before demo run.",
  },
];

export const incidents: Incident[] = [
  {
    id: "INC-021",
    title: "Battery monitoring warning",
    status: "acknowledged",
    severity: "warning",
    timestamp: "14:22",
    description: "Battery dropped below the preferred demo threshold.",
  },
  {
    id: "INC-020",
    title: "Reservation API timeout",
    status: "resolved",
    severity: "error",
    timestamp: "13:54",
    description: "Mock API exceeded the 3s validation target during test.",
  },
];
