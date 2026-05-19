import type { RobotStatus } from "../../types/admin";
import type { RobotStatusProvider } from "./robotStatusProvider";
import { appendMetricPoints } from "../timeSeriesStore";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

type RobotStatusMessage = RobotStatus & { sentAt: string };

export function createLaravelEchoRobotDataProvider(
  manager: WebSocketConnectionManager,
): RobotStatusProvider {
  let cache: RobotStatus | null = null;

  manager.echo
    .channel("robot-dashboard")
    .listen("RobotStatusUpdated", (data: RobotStatusMessage) => {
      const { sentAt, ...robotStatus } = data;
      cache = robotStatus as RobotStatus;
      const latency = Date.now() - new Date(sentAt).getTime();
      void appendMetricPoints(cache, latency);
    });

  return {
    async fetchRobotStatus() {
      if (!cache) {
        throw new Error("No robot status received yet");
      }
      return structuredClone(cache);
    },

    async setEmergencyStopState(isActive) {
      // Requires client events on private-robot-dashboard channel in Reverb config
      const channel = manager.echo.connector.pusher.channel("private-robot-dashboard");
      if (channel?.trigger) {
        channel.trigger("client-EmergencyStopRequested", { isActive });
      }
      return Promise.resolve();
    },
  };
}
