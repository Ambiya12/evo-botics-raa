import { IncidentMonitoringPanel } from "../components/admin/IncidentMonitoringPanel";
import type { Incident } from "../types/admin";

interface IncidentsPageProps {
  incidents: Incident[];
  onAcknowledge: (id: string) => Promise<void>;
}

export function IncidentsPage({ incidents, onAcknowledge }: IncidentsPageProps) {
  return <IncidentMonitoringPanel incidents={incidents} onAcknowledge={onAcknowledge} />;
}
