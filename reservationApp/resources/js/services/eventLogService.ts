import { eventLogs } from "../data/mockAdminData";
import type { EventLog } from "../types/admin";

export interface EventLogProvider {
  fetchRecentEventLogs: () => Promise<EventLog[]>;
}

const mockEventLogProvider: EventLogProvider = {
  async fetchRecentEventLogs() {
    return Promise.resolve(structuredClone(eventLogStore));
  },
};

let eventLogStore: EventLog[] = structuredClone(eventLogs);

function createEventLogId(): string {
  return `LOG-${Date.now()}`;
}

let provider: EventLogProvider = mockEventLogProvider;

export function setEventLogProvider(nextProvider: EventLogProvider): void {
  provider = nextProvider;
}

export async function getRecentEventLogs(): Promise<EventLog[]> {
  return provider.fetchRecentEventLogs();
}

export async function addEventLog(entry: Omit<EventLog, "id">): Promise<EventLog> {
  const nextLog: EventLog = {
    id: createEventLogId(),
    ...entry,
  };

  eventLogStore = [nextLog, ...eventLogStore];
  return Promise.resolve(structuredClone(nextLog));
}
