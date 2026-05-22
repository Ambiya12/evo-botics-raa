import type { EventLog } from "../../types/admin";
import type { EventLogProvider } from "../eventLogService";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

const MAX_LOGS = 200;

export function createLaravelEchoEventLogProvider(
  manager: WebSocketConnectionManager,
): EventLogProvider {
  const cache: EventLog[] = [];

  manager.echo
    .channel("robot-dashboard")
    .listen("EventLogCreated", (data: EventLog) => {
      cache.unshift(data);
      if (cache.length > MAX_LOGS) cache.pop();
    });

  return {
    async fetchRecentEventLogs() {
      return structuredClone(cache);
    },
  };
}
