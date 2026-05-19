import { robotStatus } from "../data/mockAdminData";
import type { RobotStatus } from "../types/admin";

export interface RobotStatusProvider {
  fetchRobotStatus: () => Promise<RobotStatus>;
}

const mockRobotStatusProvider: RobotStatusProvider = {
  async fetchRobotStatus() {
    return Promise.resolve(structuredClone(robotStatus));
  },
};

let provider: RobotStatusProvider = mockRobotStatusProvider;

export function setRobotStatusProvider(nextProvider: RobotStatusProvider): void {
  provider = nextProvider;
}

export async function getRobotStatus(): Promise<RobotStatus> {
  return provider.fetchRobotStatus();
}
