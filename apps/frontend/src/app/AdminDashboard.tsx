import {
  AlertTriangle,
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
import { RobotStatusOverview } from "../components/admin/RobotStatusOverview";
import {
  eventLogs,
  incidents,
  navigationItems,
} from "../data/mockAdminData";
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

function EventLogTable({ logs }: { logs: EventLog[] }) {
  return (
    <section className="panel panel--wide">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Phase 2 logging</p>
          <h3>Recent events</h3>
        </div>
        <StatusBadge label={`${logs.length} events`} />
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>Source</th>
              <th>Severity</th>
              <th>Message</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id}>
                <td>{log.timestamp}</td>
                <td>{log.source}</td>
                <td>
                  <StatusBadge
                    label={log.severity}
                    tone={
                      log.severity === "critical"
                        ? "danger"
                        : log.severity === "warning"
                          ? "warning"
                          : log.severity === "error"
                            ? "danger"
                            : "neutral"
                    }
                  />
                </td>
                <td>{log.message}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function IncidentList({ items }: { items: Incident[] }) {
  return (
    <section className="panel">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Staff exceptions</p>
          <h3>Incidents</h3>
        </div>
        <AlertTriangle aria-hidden="true" size={20} />
      </div>

      <div className="incident-list">
        {items.map((incident) => (
          <article className="incident-item" key={incident.id}>
            <div>
              <strong>{incident.title}</strong>
              <p>{incident.description}</p>
              <span>{incident.timestamp}</span>
            </div>
            <StatusBadge
              label={incident.status}
              tone={incident.status === "resolved" ? "success" : "warning"}
            />
          </article>
        ))}
      </div>
    </section>
  );
}

function SafetyActions() {
  return (
    <section className="panel safety-panel">
      <div className="panel__header">
        <div>
          <p className="section-kicker">Safety controls</p>
          <h3>Operator actions</h3>
        </div>
        <ShieldCheck aria-hidden="true" size={21} />
      </div>

      <button className="emergency-button" type="button">
        <CircleStop aria-hidden="true" size={20} />
        Emergency stop
      </button>

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

    void loadStatus();
    void loadSession();
    const intervalId = window.setInterval(() => {
      void loadStatus();
      void loadSession();
    }, 5000);

    return () => {
      mounted = false;
      window.clearInterval(intervalId);
    };
  }, []);

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
          <SafetyActions />
          <EventLogTable logs={eventLogs} />
          <IncidentList items={incidents} />
        </div>
      </main>
    </div>
  );
}
