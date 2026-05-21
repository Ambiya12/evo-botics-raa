import type { Incident } from "../../types/admin";
import type { IncidentProvider } from "../incidentService";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

export function createLaravelEchoIncidentProvider(
  manager: WebSocketConnectionManager,
): IncidentProvider {
  let cache: Incident[] = [];

  manager.echo
    .channel("robot-dashboard")
    .listen("IncidentUpdated", (data: Incident) => {
      const exists = cache.some((i) => i.id === data.id);
      cache = exists
        ? cache.map((i) => (i.id === data.id ? data : i))
        : [data, ...cache];
    });

  return {
    async fetchIncidents() {
      return structuredClone(cache);
    },

    async acknowledgeIncident(incidentId) {
      // Requires client events on private-robot-dashboard channel in Reverb config
      const channel = manager.echo.connector.pusher.channel("private-robot-dashboard");
      if (channel?.trigger) {
        channel.trigger("client-IncidentAcknowledged", { incidentId });
      }
      return Promise.resolve();
    },
  };
}
