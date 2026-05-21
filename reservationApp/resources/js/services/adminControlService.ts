import { addEventLog } from "./eventLogService";
import { addIncident } from "./incidentService";
import { getRobotStatus, setEmergencyStopState } from "./robotStatusService";

export interface EmergencyStopResult {
  timestamp: string;
  incidentId: string;
}

export interface AdminControlProvider {
  triggerEmergencyStop: () => Promise<EmergencyStopResult>;
}

const mockAdminControlProvider: AdminControlProvider = {
  async triggerEmergencyStop() {
    const robot = await getRobotStatus();

    if (robot.emergencyStop) {
      return {
        timestamp: new Date().toISOString(),
        incidentId: "already-active",
      };
    }

    const triggeredAt = new Date();
    const timestamp = triggeredAt.toISOString();

    await setEmergencyStopState(true);

    const incident = await addIncident({
      title: "Emergency stop triggered",
      status: "open",
      severity: "critical",
      timestamp: triggeredAt.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
      description: "Operator initiated emergency stop from admin safety controls.",
      relatedSessionId: robot.currentMissionSessionId,
    });

    await addEventLog({
      timestamp: triggeredAt.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      }),
      source: "admin",
      severity: "critical",
      message: "Emergency stop command issued by operator.",
      sessionId: robot.currentMissionSessionId,
      action: "emergency_stop",
      status: "succeeded",
    });

    return {
      timestamp,
      incidentId: incident.id,
    };
  },
};

let provider: AdminControlProvider = mockAdminControlProvider;

export function setAdminControlProvider(nextProvider: AdminControlProvider): void {
  provider = nextProvider;
}

export async function triggerEmergencyStop(): Promise<EmergencyStopResult> {
  return provider.triggerEmergencyStop();
}
