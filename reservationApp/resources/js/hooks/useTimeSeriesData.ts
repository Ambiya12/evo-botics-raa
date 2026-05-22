import { useLiveQuery } from "dexie-react-hooks";
import { db, type MetricName, type MetricPoint } from "../services/timeSeriesStore";

export function useTimeSeriesData(
  metric: MetricName,
  windowMinutes: 15 | 60 | 1440,
): MetricPoint[] {
  const since = Date.now() - windowMinutes * 60 * 1000;

  const raw = useLiveQuery(
    () =>
      db.metrics
        .where("[metric+timestamp]")
        .between([metric, since], [metric, Infinity])
        .sortBy("timestamp"),
    [metric, windowMinutes],
  );

  // Dexie 4 returns readonly objects from IndexedDB. Recharts mutates data
  // points internally (adds tracking props) and throws on readonly objects.
  return raw?.map((p) => ({ ...p })) ?? [];
}
