import type { RobotStatus } from "../types/admin";
import { createMockRobotDataProvider } from "./providers/mockRobotDataProvider";
import type { RobotStatusProvider } from "./providers/robotStatusProvider";

const defaultProvider: RobotStatusProvider = createMockRobotDataProvider();

let provider: RobotStatusProvider = defaultProvider;

export function setRobotStatusProvider(nextProvider: RobotStatusProvider): void {
  provider = nextProvider;
}

export function resetRobotStatusProvider(): void {
  provider = defaultProvider;
}

export async function getRobotStatus(): Promise<RobotStatus> {
  return provider.fetchRobotStatus();
}

export async function setEmergencyStopState(isActive: boolean): Promise<void> {
  return provider.setEmergencyStopState(isActive);
}
