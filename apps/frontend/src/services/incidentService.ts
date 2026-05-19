import { incidents as seedIncidents } from "../data/mockAdminData";
import type { Incident } from "../types/admin";

export interface IncidentProvider {
  fetchIncidents: () => Promise<Incident[]>;
  acknowledgeIncident: (incidentId: string) => Promise<void>;
}

let incidentStore: Incident[] = structuredClone(seedIncidents);

const mockIncidentProvider: IncidentProvider = {
  async fetchIncidents() {
    return Promise.resolve(structuredClone(incidentStore));
  },

  async acknowledgeIncident(incidentId) {
    incidentStore = incidentStore.map((incident) => {
      if (incident.id !== incidentId || incident.status !== "open") {
        return incident;
      }

      return {
        ...incident,
        status: "acknowledged",
      };
    });

    return Promise.resolve();
  },
};

let provider: IncidentProvider = mockIncidentProvider;

export function setIncidentProvider(nextProvider: IncidentProvider): void {
  provider = nextProvider;
}

export async function getIncidents(): Promise<Incident[]> {
  return provider.fetchIncidents();
}

export async function acknowledgeIncidentById(incidentId: string): Promise<void> {
  await provider.acknowledgeIncident(incidentId);
}
