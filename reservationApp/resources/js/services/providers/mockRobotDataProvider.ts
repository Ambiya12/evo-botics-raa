import { robotStatus as seedRobotStatus } from "../../data/mockAdminData";
import type { RobotStatus } from "../../types/admin";
import type { RobotStatusProvider } from "./robotStatusProvider";

function toTimeLabel(date: Date): string {
  return date.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function createMockRobotDataProvider(
  initialRobotStatus: RobotStatus = seedRobotStatus,
): RobotStatusProvider {
  let robotStatusStore: RobotStatus = structuredClone(initialRobotStatus);

  return {
    async fetchRobotStatus() {
      return Promise.resolve(structuredClone(robotStatusStore));
    },

    async setEmergencyStopState(isActive) {
      robotStatusStore = {
        ...robotStatusStore,
        state: isActive ? "EMERGENCY_STOP" : "IDLE",
        emergencyStop: isActive,
        lastUpdate: toTimeLabel(new Date()),
        lastIncidentSummary: isActive
          ? "Emergency stop triggered by operator"
          : robotStatusStore.lastIncidentSummary,
      };

      robotStatusStore.services = robotStatusStore.services.map((service) => {
        if (service.name !== "Navigation") {
          return service;
        }

        return {
          ...service,
          status: isActive ? "degraded" : "mock",
          detail: isActive
            ? "Emergency stop active in mock mode"
            : "Nav2 bridge placeholder",
        };
      });

      return Promise.resolve();
    },
  };
}
