import type { ConnectionStatus } from "../../types/admin";

type StatusListener = (status: ConnectionStatus) => void;

let currentStatus: ConnectionStatus = "mock";
const listeners = new Set<StatusListener>();

export function setConnectionManagerStatus(status: ConnectionStatus): void {
  currentStatus = status;
  for (const fn of listeners) fn(status);
}

export function getConnectionManagerStatus(): ConnectionStatus {
  return currentStatus;
}

export function subscribeConnectionStatus(
  listener: StatusListener,
): () => void {
  listeners.add(listener);
  listener(currentStatus);
  return () => listeners.delete(listener);
}
