import Echo from "laravel-echo";
import Pusher from "pusher-js";
import type { ConnectionStatus } from "../../types/admin";

declare global {
  interface Window {
    Pusher: typeof Pusher;
  }
}

type StatusListener = (status: ConnectionStatus) => void;

export interface WebSocketConnectionManager {
  readonly echo: Echo<"reverb">;
  readonly status: ConnectionStatus;
  subscribe(listener: StatusListener): () => void;
  destroy(): void;
}

export function createWebSocketConnectionManager(
  wsUrl: string,
  appKey: string,
): WebSocketConnectionManager {
  window.Pusher = Pusher;

  const url = new URL(wsUrl);
  const isTls = url.protocol === "wss:";

  const echo = new Echo({
    broadcaster: "reverb",
    key: appKey,
    wsHost: url.hostname,
    wsPort: isTls ? undefined : Number(url.port) || 80,
    wssPort: isTls ? Number(url.port) || 443 : undefined,
    forceTLS: isTls,
    enabledTransports: ["ws", "wss"],
  });

  let currentStatus: ConnectionStatus = "connecting";
  const listeners = new Set<StatusListener>();

  function notify(next: ConnectionStatus): void {
    currentStatus = next;
    for (const fn of listeners) fn(next);
  }

  const pusher = echo.connector.pusher;
  let retryCount = 0;

  pusher.connection.bind("connected", () => {
    retryCount = 0;
    notify("connected_ros");
  });
  pusher.connection.bind("disconnected", () => notify("disconnected"));
  pusher.connection.bind("error", () => notify("error"));
  pusher.connection.bind("unavailable", () => {
    notify("disconnected");
    const delay = Math.min(1_000 * 2 ** retryCount, 30_000);
    retryCount++;
    setTimeout(() => pusher.connection.connect(), delay);
  });

  return {
    get echo() {
      return echo;
    },
    get status() {
      return currentStatus;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    destroy() {
      echo.disconnect();
      listeners.clear();
    },
  };
}
