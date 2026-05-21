import { describe, it, expect, beforeEach } from "vitest";
import "fake-indexeddb/auto";
import {
  appendMetricPoints,
  queryMetrics,
  pruneOldMetrics,
  db,
} from "../timeSeriesStore";
import type { RobotStatus } from "../../types/admin";

const mockRobotStatus: RobotStatus = {
  id: "test-robot",
  name: "Test Robot",
  mode: "mock",
  connectionStatus: "mock",
  state: "GUIDING",
  battery: 75,
  location: "Hall",
  currentWaypoint: "wp-01",
  destination: "Room A",
  currentMissionSessionId: null,
  lastIncidentSummary: "",
  lastUpdate: "10:00:00",
  emergencyStop: false,
  services: [],
};

beforeEach(async () => {
  await db.metrics.clear();
});

describe("appendMetricPoints", () => {
  it("writes 3 points (battery, navState, latency) per call", async () => {
    await appendMetricPoints(mockRobotStatus, 42);
    const all = await db.metrics.toArray();
    expect(all).toHaveLength(3);
    expect(all.map((p) => p.metric).sort()).toEqual([
      "battery",
      "latency",
      "navState",
    ]);
  });

  it("stores the correct battery value", async () => {
    await appendMetricPoints(mockRobotStatus, 0);
    const [point] = await db.metrics
      .where("metric")
      .equals("battery")
      .toArray();
    expect(point.value).toBe(75);
  });

  it("stores the correct latency value", async () => {
    await appendMetricPoints(mockRobotStatus, 123);
    const [point] = await db.metrics
      .where("metric")
      .equals("latency")
      .toArray();
    expect(point.value).toBe(123);
  });
});

describe("queryMetrics", () => {
  it("returns only points within the time window", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 10_000, metric: "battery", value: 80 },
      { timestamp: now - 5_000, metric: "battery", value: 70 },
      { timestamp: now - 90 * 60 * 1000, metric: "battery", value: 60 },
    ]);
    const points = await queryMetrics("battery", now - 60 * 60 * 1000);
    expect(points).toHaveLength(2);
    expect(points.every((p) => p.metric === "battery")).toBe(true);
  });

  it("returns points sorted by timestamp ascending", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 5_000, metric: "latency", value: 50 },
      { timestamp: now - 10_000, metric: "latency", value: 100 },
    ]);
    const points = await queryMetrics("latency", now - 60_000);
    expect(points[0].value).toBe(100);
    expect(points[1].value).toBe(50);
  });
});

describe("pruneOldMetrics", () => {
  it("deletes points older than 24h and keeps recent ones", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 25 * 60 * 60 * 1000, metric: "battery", value: 50 },
      { timestamp: now - 1_000, metric: "battery", value: 80 },
    ]);
    await pruneOldMetrics();
    const remaining = await db.metrics.toArray();
    expect(remaining).toHaveLength(1);
    expect(remaining[0].value).toBe(80);
  });
});
