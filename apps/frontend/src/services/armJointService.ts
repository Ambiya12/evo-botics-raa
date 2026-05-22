import type { ArmJoint } from "../types/admin";
import { createMockArmJointProvider } from "./providers/mockArmJointProvider";
import type { ArmJointProvider } from "./providers/armJointProvider";

const defaultProvider: ArmJointProvider = createMockArmJointProvider();

let provider: ArmJointProvider = defaultProvider;

export function setArmJointProvider(nextProvider: ArmJointProvider): void {
  provider = nextProvider;
}

export function resetArmJointProvider(): void {
  provider = defaultProvider;
}

export async function getArmJoints(): Promise<ArmJoint[]> {
  return provider.fetchArmJoints();
}
