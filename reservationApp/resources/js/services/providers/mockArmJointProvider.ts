import { armJoints as seedArmJoints } from "../../data/mockAdminData";
import type { ArmJoint } from "../../types/admin";
import type { ArmJointProvider } from "./armJointProvider";

export function createMockArmJointProvider(
  initialArmJoints: ArmJoint[] = seedArmJoints,
): ArmJointProvider {
  const store: ArmJoint[] = structuredClone(initialArmJoints);

  return {
    async fetchArmJoints() {
      return Promise.resolve(structuredClone(store));
    },
  };
}
