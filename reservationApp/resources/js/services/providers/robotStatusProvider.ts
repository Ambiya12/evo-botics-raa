import type { RobotStatus } from "../../types/admin";

export interface RobotStatusProvider {
  fetchRobotStatus: () => Promise<RobotStatus>;
  setEmergencyStopState: (isActive: boolean) => Promise<void>;
}
