import { useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Panel } from "../ui/Panel";
import { useTimeSeriesData } from "../../hooks/useTimeSeriesData";
import type { MetricName, MetricPoint } from "../../services/timeSeriesStore";

type WindowMinutes = 15 | 60 | 1440;

const WINDOW_OPTIONS: Array<{ label: string; value: WindowMinutes }> = [
  { label: "15 min", value: 15 },
  { label: "1h", value: 60 },
  { label: "24h", value: 1440 },
];

const NAV_STATE_LABELS: Record<number, string> = {
  0: "IDLE",
  1: "QR WAIT",
  2: "VALIDATING",
  3: "GUIDING",
  4: "ARRIVED",
  5: "RETURNING",
  6: "ERROR",
  7: "E-STOP",
};

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface MetricChartProps {
  metric: MetricName;
  windowMinutes: WindowMinutes;
  yDomain?: [number, number];
  yTickFormatter?: (value: number) => string;
  tooltipFormatter?: (value: number) => string;
}

function MetricChart({
  metric,
  windowMinutes,
  yDomain,
  yTickFormatter,
  tooltipFormatter,
}: MetricChartProps) {
  const points: MetricPoint[] = useTimeSeriesData(metric, windowMinutes);

  if (points.length === 0) {
    return (
      <p className="timeseries-empty">No data — waiting for robot connection</p>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={140}>
      <LineChart data={points}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #e5e7eb)" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatTime}
          tick={{ fontSize: 10 }}
          stroke="var(--text-muted, #9ca3af)"
        />
        <YAxis
          domain={yDomain}
          tickFormatter={yTickFormatter}
          tick={{ fontSize: 10 }}
          stroke="var(--text-muted, #9ca3af)"
          width={48}
        />
        <Tooltip
          labelFormatter={(label) =>
            new Date(label as number).toLocaleTimeString()
          }
          formatter={(value) => [
            tooltipFormatter ? tooltipFormatter(value as number) : String(value),
            metric,
          ]}
        />
        <Line
          type="monotone"
          dataKey="value"
          dot={false}
          stroke="var(--accent, #3b82f6)"
          strokeWidth={1.5}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function TimeSeriesPanel() {
  const [window, setWindow] = useState<WindowMinutes>(15);

  return (
    <Panel title="Telemetry" eyebrow="Time series" className="timeseries-panel">
      <div className="timeseries-controls">
        {WINDOW_OPTIONS.map(({ label, value }) => (
          <button
            key={value}
            type="button"
            className={`timeseries-btn${window === value ? " timeseries-btn--active" : ""}`}
            onClick={() => setWindow(value)}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="timeseries-charts">
        <div>
          <p className="timeseries-label">Battery (%)</p>
          <MetricChart
            metric="battery"
            windowMinutes={window}
            yDomain={[0, 100]}
            yTickFormatter={(v) => `${v}%`}
            tooltipFormatter={(v) => `${v}%`}
          />
        </div>

        <div>
          <p className="timeseries-label">Navigation state</p>
          <MetricChart
            metric="navState"
            windowMinutes={window}
            yDomain={[0, 7]}
            yTickFormatter={(v) => NAV_STATE_LABELS[v] ?? String(v)}
            tooltipFormatter={(v) => NAV_STATE_LABELS[v] ?? String(v)}
          />
        </div>

        <div>
          <p className="timeseries-label">Latency (ms)</p>
          <MetricChart
            metric="latency"
            windowMinutes={window}
            tooltipFormatter={(v) => `${v} ms`}
          />
        </div>
      </div>
    </Panel>
  );
}
