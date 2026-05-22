import type { VisitorSession } from "../../types/admin";
import type { VisitorSessionProvider } from "../visitorSessionService";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

export function createLaravelEchoVisitorSessionProvider(
  manager: WebSocketConnectionManager,
): VisitorSessionProvider {
  let cache: VisitorSession | null = null;

  manager.echo
    .channel("robot-dashboard")
    .listen("VisitorSessionUpdated", (data: VisitorSession) => {
      cache = data;
    });

  return {
    async fetchCurrentSession() {
      return cache ? structuredClone(cache) : null;
    },
  };
}
