import type { ArmJoint } from "../../types/admin";

export interface ArmJointProvider {
  fetchArmJoints: () => Promise<ArmJoint[]>;
}
