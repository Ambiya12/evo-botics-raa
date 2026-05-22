import { SafetyActions } from "../SafetyActions";

interface SafetyPageProps {
  emergencyStopActive: boolean;
  onEmergencyStop: () => Promise<void>;
}

export function SafetyPage({ emergencyStopActive, onEmergencyStop }: SafetyPageProps) {
  return <SafetyActions emergencyStopActive={emergencyStopActive} onEmergencyStop={onEmergencyStop} />;
}
