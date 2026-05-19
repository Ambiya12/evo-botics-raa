import { useMemo, useState } from "react";
import { AdminShell } from "../components/admin/AdminShell";
import { CurrentVisitorSessionPanel } from "../components/admin/CurrentVisitorSessionPanel";
import { EventLogTable } from "../components/admin/EventLogTable";
import { IncidentMonitoringPanel } from "../components/admin/IncidentMonitoringPanel";
import { RobotHealthPanel } from "../components/admin/RobotHealthPanel";
import { RobotStatusOverview } from "../components/admin/RobotStatusOverview";
import { SafetyActions } from "../components/admin/SafetyActions";
import { DashboardSkeleton } from "../components/ui/Skeleton";
import { useDashboardData } from "../hooks/useDashboardData";
import type { EventLog, Incident } from "../types/admin";

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
  const {
    robotStatus,
    currentSession,
    eventLogs,
    incidents,
    isLoading,
    isRefreshing,
    error,
    lastSyncedAt,
    refresh,
    acknowledgeIncident,
    requestEmergencyStop,
  } = useDashboardData();

  const normalizedSearchQuery = searchQuery.trim().toLowerCase();

  const filteredLogs = useMemo(() => {
    if (!normalizedSearchQuery) {
      return eventLogs;
    }

    return eventLogs.filter((log) => matchesLog(log, normalizedSearchQuery));
  }, [eventLogs, normalizedSearchQuery]);

  const filteredIncidents = useMemo(() => {
    if (!normalizedSearchQuery) {
      return incidents;
    }

    return incidents.filter((incident) => matchesIncident(incident, normalizedSearchQuery));
  }, [incidents, normalizedSearchQuery]);

  return (
    <AdminShell
      searchQuery={searchQuery}
      onSearchQueryChange={setSearchQuery}
      lastSyncedAt={lastSyncedAt}
      isRefreshing={isRefreshing}
      onRefresh={() => {
        void refresh();
      }}
    >
      {error ? (
        <div className="dashboard-alert" role="alert">
          {error}
        </div>
      ) : null}

      {isLoading || !robotStatus ? (
        <section className="panel">
          <DashboardSkeleton rows={6} />
        </section>
      ) : (
        <>
          <RobotStatusOverview robotStatus={robotStatus} />
          <div className="dashboard-grid">
            <RobotHealthPanel robotStatus={robotStatus} />
            <CurrentVisitorSessionPanel session={currentSession} />
            <SafetyActions
              emergencyStopActive={robotStatus.emergencyStop}
              onEmergencyStop={requestEmergencyStop}
            />
            <EventLogTable logs={filteredLogs} />
            <IncidentMonitoringPanel
              incidents={filteredIncidents}
              onAcknowledge={acknowledgeIncident}
            />
          </div>
        </>
      )}
    </AdminShell>
  );
}
