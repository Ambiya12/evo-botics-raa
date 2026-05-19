import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { triggerEmergencyStop } from "../services/adminControlService";
import { getRecentEventLogs } from "../services/eventLogService";
import { acknowledgeIncidentById, getIncidents } from "../services/incidentService";
import { getRobotStatus } from "../services/robotStatusService";
import { getCurrentVisitorSession } from "../services/visitorSessionService";
import type { EventLog, Incident, RobotStatus, VisitorSession } from "../types/admin";

interface DashboardDataState {
  robotStatus: RobotStatus | null;
  currentSession: VisitorSession | null;
  eventLogs: EventLog[];
  incidents: Incident[];
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastSyncedAt: string | null;
}

const initialState: DashboardDataState = {
  robotStatus: null,
  currentSession: null,
  eventLogs: [],
  incidents: [],
  isLoading: true,
  isRefreshing: false,
  error: null,
  lastSyncedAt: null,
};

function toSyncTimeLabel(date: Date): string {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function useDashboardData() {
  const [state, setState] = useState<DashboardDataState>(initialState);
  const mountedRef = useRef(false);

  const refresh = useCallback(async () => {
    setState((current) => ({
      ...current,
      isRefreshing: true,
      error: null,
    }));

    try {
      const [robotStatus, currentSession, eventLogs, incidents] = await Promise.all([
        getRobotStatus(),
        getCurrentVisitorSession(),
        getRecentEventLogs(),
        getIncidents(),
      ]);

      if (!mountedRef.current) {
        return;
      }

      setState({
        robotStatus,
        currentSession,
        eventLogs,
        incidents,
        isLoading: false,
        isRefreshing: false,
        error: null,
        lastSyncedAt: toSyncTimeLabel(new Date()),
      });
    } catch {
      if (!mountedRef.current) {
        return;
      }

      setState((current) => ({
        ...current,
        isLoading: false,
        isRefreshing: false,
        error: "Unable to refresh dashboard data.",
      }));
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    void refresh();

    const intervalId = window.setInterval(() => {
      void refresh();
    }, 5000);

    return () => {
      mountedRef.current = false;
      window.clearInterval(intervalId);
    };
  }, [refresh]);

  const acknowledgeIncident = useCallback(
    async (incidentId: string) => {
      await acknowledgeIncidentById(incidentId);
      await refresh();
    },
    [refresh],
  );

  const requestEmergencyStop = useCallback(async () => {
    await triggerEmergencyStop();
    await refresh();
  }, [refresh]);

  return useMemo(
    () => ({
      ...state,
      refresh,
      acknowledgeIncident,
      requestEmergencyStop,
    }),
    [acknowledgeIncident, refresh, requestEmergencyStop, state],
  );
}
