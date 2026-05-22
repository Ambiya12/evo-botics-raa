import { useMemo, useState } from "react";
import { AdminShell } from "./AdminShell";
import { DashboardSkeleton } from "../ui/Skeleton";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { useDashboardData } from "../../hooks/useDashboardData";
import { IncidentsPage } from "./pages/IncidentsPage";
import { LiveStatusPage } from "./pages/LiveStatusPage";
import { MapPage } from "./pages/MapPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SafetyPage } from "./pages/SafetyPage";
import { SessionsPage } from "./pages/SessionsPage";
import { SettingsPage } from "./pages/SettingsPage";
import type { EventLog, Incident } from "../../types/admin";

function matchesLog(log: EventLog, query: string): boolean {
  const haystack = [
    log.timestamp,
    log.source,
    log.severity,
    log.message,
    log.sessionId ?? "",
    log.action,
    log.status,
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(query);
}

function matchesIncident(incident: Incident, query: string): boolean {
  const haystack = [
    incident.title,
    incident.status,
    incident.severity,
    incident.timestamp,
    incident.description,
    incident.relatedSessionId ?? "",
  ]
    .join(" ")
    .toLowerCase();

  return haystack.includes(query);
}

export function AdminDashboard() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activePage, setActivePage] = useState("overview");

  const {
    robotStatus,
    currentSession,
    eventLogs,
    incidents,
    isLoading,
    isRefreshing,
    error,
    lastSyncedAt,
    connectionStatus,
    refresh,
    acknowledgeIncident,
    requestEmergencyStop,
  } = useDashboardData();

  const normalizedSearchQuery = searchQuery.trim().toLowerCase();

  const filteredLogs = useMemo(() => {
    if (!normalizedSearchQuery) return eventLogs;
    return eventLogs.filter((log) => matchesLog(log, normalizedSearchQuery));
  }, [eventLogs, normalizedSearchQuery]);

  const filteredIncidents = useMemo(() => {
    if (!normalizedSearchQuery) return incidents;
    return incidents.filter((incident) => matchesIncident(incident, normalizedSearchQuery));
  }, [incidents, normalizedSearchQuery]);

  function renderPage() {
    if (isLoading || !robotStatus) {
      return (
        <section className="panel">
          <DashboardSkeleton rows={6} />
        </section>
      );
    }

    switch (activePage) {
      case "live-status":
        return <LiveStatusPage />;
      case "sessions":
        return <SessionsPage currentSession={currentSession} logs={filteredLogs} />;
      case "incidents":
        return <IncidentsPage incidents={filteredIncidents} onAcknowledge={acknowledgeIncident} />;
      case "map":
        return <MapPage />;
      case "safety":
        return (
          <SafetyPage
            emergencyStopActive={robotStatus.emergencyStop}
            onEmergencyStop={requestEmergencyStop}
          />
        );
      case "settings":
        return <SettingsPage />;
      default:
        return <OverviewPage robotStatus={robotStatus} currentSession={currentSession} />;
    }
  }

  return (
    <AdminShell
      activePage={activePage}
      onNavigate={setActivePage}
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
      lastSyncedAt={lastSyncedAt}
      isRefreshing={isRefreshing}
      onRefresh={() => {
        void refresh();
      }}
      connectionStatus={connectionStatus}
    >
      {error ? (
        <div className="dashboard-alert" role="alert">
          {error}
        </div>
      ) : null}

      <ErrorBoundary>
        {renderPage()}
      </ErrorBoundary>
    </AdminShell>
  );
}
