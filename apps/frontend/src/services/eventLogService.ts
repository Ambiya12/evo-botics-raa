import { eventLogs } from "../data/mockAdminData";
import type { EventLog } from "../types/admin";

export interface EventLogProvider {
  fetchRecentEventLogs: () => Promise<EventLog[]>;
}

const mockEventLogProvider: EventLogProvider = {
  async fetchRecentEventLogs() {
    return Promise.resolve(structuredClone(eventLogs));
  },
};

let provider: EventLogProvider = mockEventLogProvider;

export function setEventLogProvider(nextProvider: EventLogProvider): void {
  provider = nextProvider;
}

export async function getRecentEventLogs(): Promise<EventLog[]> {
  return provider.fetchRecentEventLogs();
}
