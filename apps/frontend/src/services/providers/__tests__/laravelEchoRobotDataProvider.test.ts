import { describe, it, expect, vi, beforeEach } from "vitest";
import "fake-indexeddb/auto";
import { db } from "../../timeSeriesStore";

vi.mock("laravel-echo", () => ({ default: vi.fn() }));
vi.mock("pusher-js", () => ({ default: vi.fn() }));

import { createLaravelEchoRobotDataProvider } from "../laravelEchoRobotDataProvider";
import type { WebSocketConnectionManager } from "../websocketConnectionManager";
import type { RobotStatus } from "../../../types/admin";

type EventHandler = (data: unknown) => void;

function makeManager(): {
  manager: WebSocketConnectionManager;
  emit: (event: string, data: unknown) => void;
} {
  const handlers: Record<string, EventHandler> = {};
  const channelMock = {
    listen: vi.fn().mockImplementation((event: string, handler: EventHandler) => {
      handlers[event] = handler;
      return channelMock;
    }),
  };
  const manager: WebSocketConnectionManager = {
    echo: {
      channel: vi.fn().mockReturnValue(channelMock),
      connector: { pusher: { channel: vi.fn().mockReturnValue(null) } },
    } as unknown as WebSocketConnectionManager["echo"],
    status: "connected_ros",
    subscribe: vi.fn(),
    destroy: vi.fn(),
  };
  return {
    manager,
    emit: (event, data) => handlers[event]?.(data),
  };
}

const baseMessage: RobotStatus & { sentAt: string } = {
  id: "r1",
  name: "Robot",
  mode: "rosbridge",
  connectionStatus: "connected_ros",
  state: "GUIDING",
  battery: 80,
  location: "Hall",
  currentWaypoint: "wp-01",
  destination: "Room B",
  currentMissionSessionId: null,
  lastIncidentSummary: "",
  lastUpdate: "10:00:00",
  emergencyStop: false,
  services: [],
  sentAt: new Date().toISOString(),
};

beforeEach(async () => {
  await db.metrics.clear();
});

describe("createLaravelEchoRobotDataProvider", () => {
  it("rejects fetchRobotStatus before first WebSocket message", async () => {
    const { manager } = makeManager();
    const provider = createLaravelEchoRobotDataProvider(manager);
    await expect(provider.fetchRobotStatus()).rejects.toThrow(
      "No robot status received yet",
    );
  });

  it("returns cached status after receiving RobotStatusUpdated", async () => {
    const { manager, emit } = makeManager();
    const provider = createLaravelEchoRobotDataProvider(manager);
    emit("RobotStatusUpdated", baseMessage);
    const status = await provider.fetchRobotStatus();
    expect(status.battery).toBe(80);
  });

  it("does not expose sentAt on the returned status", async () => {
    const { manager, emit } = makeManager();
    const provider = createLaravelEchoRobotDataProvider(manager);
    emit("RobotStatusUpdated", baseMessage);
    const status = await provider.fetchRobotStatus();
    expect((status as Record<string, unknown>)["sentAt"]).toBeUndefined();
  });

  it("writes 3 metric points to IndexedDB on each update", async () => {
    const { manager, emit } = makeManager();
    createLaravelEchoRobotDataProvider(manager);
    emit("RobotStatusUpdated", baseMessage);
    await new Promise((r) => setTimeout(r, 50));
    const points = await db.metrics.toArray();
    expect(points).toHaveLength(3);
  });
});
