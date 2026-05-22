import Dexie, { type Table } from "dexie";
import type { RobotStatus, RobotState } from "../types/admin";

export type MetricName = "battery" | "navState" | "latency";

export interface MetricPoint {
  id?: number;
  timestamp: number;
  metric: MetricName;
  value: number;
}

const NAV_STATE_INDEX: Record<RobotState, number> = {
  IDLE: 0,
  WAITING_FOR_QR: 1,
  VALIDATING_RESERVATION: 2,
  GUIDING: 3,
  ARRIVED: 4,
  RETURNING_HOME: 5,
  ERROR: 6,
  EMERGENCY_STOP: 7,
};

const RETENTION_MS = 24 * 60 * 60 * 1000;

class RobotMetricsDb extends Dexie {
  metrics!: Table<MetricPoint, number>;

  constructor() {
    super("robot-metrics");
    this.version(1).stores({
      metrics: "++id, [metric+timestamp], timestamp, metric",
    });
  }
}

export const db = new RobotMetricsDb();

export async function pruneOldMetrics(): Promise<void> {
  const cutoff = Date.now() - RETENTION_MS;
  await db.metrics.where("timestamp").below(cutoff).delete();
}

export async function appendMetricPoints(
  robotStatus: RobotStatus,
  latencyMs: number,
): Promise<void> {
  const now = Date.now();
  await db.metrics.bulkAdd([
    { timestamp: now, metric: "battery", value: robotStatus.battery },
    {
      timestamp: now,
      metric: "navState",
      value: NAV_STATE_INDEX[robotStatus.state],
    },
    { timestamp: now, metric: "latency", value: latencyMs },
  ]);
}

export async function queryMetrics(
  metric: MetricName,
  since: number,
): Promise<MetricPoint[]> {
  return db.metrics
    .where("[metric+timestamp]")
    .between([metric, since], [metric, Infinity])
    .sortBy("timestamp");
}
