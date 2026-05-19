import { useLiveQuery } from "dexie-react-hooks";
import { db, type MetricName, type MetricPoint } from "../services/timeSeriesStore";

export function useTimeSeriesData(
  metric: MetricName,
  windowMinutes: 15 | 60 | 1440,
): MetricPoint[] {
  const since = Date.now() - windowMinutes * 60 * 1000;

  return (
    useLiveQuery(
      () =>
        db.metrics
          .where("[metric+timestamp]")
          .between([metric, since], [metric, Infinity])
          .sortBy("timestamp"),
      [metric, windowMinutes],
    ) ?? []
  );
}
