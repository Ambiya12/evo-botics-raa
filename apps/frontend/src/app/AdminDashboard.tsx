import {
  Bell,
  CircleStop,
  Pause,
  Play,
  Radio,
  RotateCcw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useEffect, useState } from "react";
import { CurrentVisitorSessionPanel } from "../components/admin/CurrentVisitorSessionPanel";
import { EventLogTable } from "../components/admin/EventLogTable";
import { IncidentMonitoringPanel } from "../components/admin/IncidentMonitoringPanel";
import { RobotStatusOverview } from "../components/admin/RobotStatusOverview";
import {
  navigationItems,
} from "../data/mockAdminData";
import { triggerEmergencyStop } from "../services/adminControlService";
import { acknowledgeIncidentById, getIncidents } from "../services/incidentService";
import { getRecentEventLogs } from "../services/eventLogService";
import { getRobotStatus } from "../services/robotStatusService";
import { getCurrentVisitorSession } from "../services/visitorSessionService";
import type { EventLog, Incident, RobotStatus, ServiceStatus, VisitorSession } from "../types/admin";

function formatStatus(status: ServiceStatus) {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function StatusBadge({
  label,
  tone = "neutral",
}: {
  label: string;
  tone?: "success" | "warning" | "danger" | "neutral" | "mock";
}) {
  return <span className={`status-badge status-badge--${tone}`}>{label}</span>;
}

function Sidebar() {
  return (
    <aside className="sidebar" aria-label="Admin navigation">
      <div className="brand">
        <div className="brand__mark">EB</div>
        <div>
          <p className="brand__eyebrow">Evo-Botics</p>
          <h1>Admin</h1>
        </div>
      </div>

      <nav className="nav-list">
        {navigationItems.map((item) => (
          <button
            className={`nav-list__item ${item.active ? "nav-list__item--active" : ""}`}
            key={item.label}
            type="button"
          >
            <item.icon aria-hidden="true" size={18} />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}

function Topbar() {
  return (
    <header className="topbar">
      <div>
        <p className="section-kicker">Operator console</p>
        <h2>Robot monitoring dashboard</h2>
      </div>
      <div className="topbar__actions">
        <label className="search" htmlFor="dashboard-search">
          <Search aria-hidden="true" size={18} />
          <input id="dashboard-search" placeholder="Search logs or sessions" type="search" />
        </label>
        <button className="icon-button" type="button" aria-label="Open notifications">
          <Bell aria-hidden="true" size={19} />
        </button>
      </div>
    </header>
  );
}

function RobotHealthPanel({ robotStatus }: { robotStatus: RobotStatus }) {
  const statusTone: Record<ServiceStatus, "success" | "warning" | "danger" | "mock"> = {
    online: "success",
    degraded: "warning",
    offline: "danger",
    mock: "mock",
  };

  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="section-kicker">System health</p>
          <h3>{robotStatus.name}</h3>
        </div>
        <StatusBadge label={robotStatus.mode.toUpperCase()} tone="mock" />
      </div>

      <div className="health-list">
        {robotStatus.services.map((service) => (
          <div className="health-row" key={service.name}>
            <div>
              <strong>{service.name}</strong>
              <span>{service.detail}</span>
            </div>
            <StatusBadge label={formatStatus(service.status)} tone={statusTone[service.status]} />
          </div>
        ))}
      </div>
    </section>
  );
}

function SafetyActions({
  emergencyStopActive,
  onEmergencyStop,
}: {
  emergencyStopActive: boolean;
  onEmergencyStop: () => Promise<void>;
}) {
  const [isConfirmingEmergencyStop, setIsConfirmingEmergencyStop] = useState(false);
  const [isSubmittingEmergencyStop, setIsSubmittingEmergencyStop] = useState(false);

  const handleEmergencyStopClick = async () => {
    if (emergencyStopActive || isSubmittingEmergencyStop) {
      return;
    }

    if (!isConfirmingEmergencyStop) {
      setIsConfirmingEmergencyStop(true);
      return;
    }

    setIsSubmittingEmergencyStop(true);

    try {
      await onEmergencyStop();
      setIsConfirmingEmergencyStop(false);
    } finally {
      setIsSubmittingEmergencyStop(false);
    }
  };

  const emergencyStopLabel = emergencyStopActive
    ? "Emergency stop active"
    : isConfirmingEmergencyStop
      ? "Confirm emergency stop"
      : "Emergency stop";

  const emergencyStopButtonClass = `emergency-button ${
    isConfirmingEmergencyStop ? "emergency-button--confirming" : ""
  }`;

  return (
    <section className="panel safety-panel">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Safety controls</p>
          <h3>Operator actions</h3>
        </div>
        <ShieldCheck aria-hidden="true" size={21} />
      </div>

      <button
        className={emergencyStopButtonClass}
        type="button"
        onClick={() => {
          void handleEmergencyStopClick();
        }}
        disabled={emergencyStopActive || isSubmittingEmergencyStop}
      >
        <CircleStop aria-hidden="true" size={20} />
        {emergencyStopLabel}
      </button>

      {!emergencyStopActive && isConfirmingEmergencyStop ? (
        <p className="safety-panel__hint">Press again to confirm the mock emergency stop command.</p>
      ) : null}

      <div className="control-grid">
        <button type="button">
          <Pause aria-hidden="true" size={18} />
          Pause
        </button>
        <button type="button">
          <Play aria-hidden="true" size={18} />
          Resume
        </button>
        <button type="button">
          <RotateCcw aria-hidden="true" size={18} />
          Return
        </button>
        <button type="button">
          <Radio aria-hidden="true" size={18} />
          Retry
        </button>
      </div>
    </section>
  );
}

export function AdminDashboard() {
  const [robotStatus, setRobotStatus] = useState<RobotStatus | null>(null);
  const [currentSession, setCurrentSession] = useState<VisitorSession | null>(null);
  const [eventLogs, setEventLogs] = useState<EventLog[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);

  const refreshDashboardData = async () => {
    const [status, session, logs, incidentItems] = await Promise.all([
      getRobotStatus(),
      getCurrentVisitorSession(),
      getRecentEventLogs(),
      getIncidents(),
    ]);

    setRobotStatus(status);
    setCurrentSession(session);
    setEventLogs(logs);
    setIncidents(incidentItems);
  };

  useEffect(() => {
    let mounted = true;

    const loadStatus = async () => {
      const status = await getRobotStatus();
      if (mounted) {
        setRobotStatus(status);
      }
    };

    const loadSession = async () => {
      const session = await getCurrentVisitorSession();
      if (mounted) {
        setCurrentSession(session);
      }
    };

    const loadEventLogs = async () => {
      const logs = await getRecentEventLogs();
      if (mounted) {
        setEventLogs(logs);
      }
    };

    const loadIncidents = async () => {
      const incidentItems = await getIncidents();
      if (mounted) {
        setIncidents(incidentItems);
      }
    };

    void loadStatus();
    void loadSession();
    void loadEventLogs();
    void loadIncidents();
    const intervalId = window.setInterval(() => {
      void loadStatus();
      void loadSession();
      void loadEventLogs();
      void loadIncidents();
    }, 5000);

    return () => {
      mounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const handleAcknowledgeIncident = async (incidentId: string) => {
    await acknowledgeIncidentById(incidentId);
    const updatedIncidents = await getIncidents();
    setIncidents(updatedIncidents);
  };

  const handleEmergencyStop = async () => {
    await triggerEmergencyStop();
    await refreshDashboardData();
  };

  if (!robotStatus) {
    return (
      <div className="app-shell">
        <Sidebar />
        <main className="dashboard">
          <Topbar />
          <section className="panel">
            <p>Loading robot status...</p>
          </section>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <Sidebar />
      <main className="dashboard">
        <Topbar />
        <RobotStatusOverview robotStatus={robotStatus} />
        <div className="dashboard-grid">
          <RobotHealthPanel robotStatus={robotStatus} />
          <CurrentVisitorSessionPanel session={currentSession} />
          <SafetyActions
            emergencyStopActive={robotStatus.emergencyStop}
            onEmergencyStop={handleEmergencyStop}
          />
          <EventLogTable logs={eventLogs} />
          <IncidentMonitoringPanel
            incidents={incidents}
            onAcknowledge={handleAcknowledgeIncident}
          />
        </div>
      </main>
    </div>
  );
}
