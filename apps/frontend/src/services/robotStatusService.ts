import { robotStatus } from "../data/mockAdminData";
import type { RobotStatus } from "../types/admin";

export interface RobotStatusProvider {
  fetchRobotStatus: () => Promise<RobotStatus>;
}

const mockRobotStatusProvider: RobotStatusProvider = {
  async fetchRobotStatus() {
    return Promise.resolve(structuredClone(robotStatusStore));
  },
};

let robotStatusStore: RobotStatus = structuredClone(robotStatus);

let provider: RobotStatusProvider = mockRobotStatusProvider;

export function setRobotStatusProvider(nextProvider: RobotStatusProvider): void {
  provider = nextProvider;
}

export async function getRobotStatus(): Promise<RobotStatus> {
  return provider.fetchRobotStatus();
}

export async function setEmergencyStopState(isActive: boolean): Promise<void> {
  robotStatusStore = {
    ...robotStatusStore,
    state: isActive ? "EMERGENCY_STOP" : "IDLE",
    emergencyStop: isActive,
    lastIncidentSummary: isActive
      ? "Emergency stop triggered by operator"
      : robotStatusStore.lastIncidentSummary,
  };

  if (isActive) {
    robotStatusStore.services = robotStatusStore.services.map((service) => {
      if (service.name !== "Navigation") {
        return service;
      }

      return {
        ...service,
        status: "degraded",
        detail: "Emergency stop active in mock mode",
      };
    });
  }

  return Promise.resolve();
}
