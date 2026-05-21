import { useEffect, useState } from "react";
import { Cpu } from "lucide-react";
import { Panel } from "../ui/Panel";
import { getJetsonMetrics } from "../../services/jetsonMetricsService";
import type { JetsonMetrics } from "../../types/admin";

const RADIUS = 36;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;

interface GaugeColorThresholds {
  warn: number;
  danger: number;
}

const PCT_THRESHOLDS: GaugeColorThresholds = { warn: 60, danger: 85 };
const TEMP_THRESHOLDS: GaugeColorThresholds = { warn: 60, danger: 75 };

function gaugeColor(value: number, thresholds: GaugeColorThresholds): string {
  if (value > thresholds.danger) return "var(--danger)";
  if (value > thresholds.warn) return "var(--warning)";
  return "var(--success)";
}

interface GaugeCardProps {
  label: string;
  value: number;
  max: number;
  unit: string;
  thresholds: GaugeColorThresholds;
}

function GaugeCard({ label, value, max, unit, thresholds }: GaugeCardProps) {
  const clamped = Math.min(Math.max(value, 0), max);
  const offset = CIRCUMFERENCE * (1 - clamped / max);
  const color = gaugeColor(clamped, thresholds);

  return (
    <div className="jetson-gauge">
      <svg width="80" height="80" viewBox="0 0 80 80">
        {/* track arc */}
        <circle
          cx="40"
          cy="40"
          r={RADIUS}
          fill="none"
          stroke="var(--line)"
          strokeWidth={7}
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={0}
          transform="rotate(-90 40 40)"
        />
        {/* fill arc */}
        <circle
          cx="40"
          cy="40"
          r={RADIUS}
          fill="none"
          stroke={color}
          strokeWidth={7}
          strokeLinecap="round"
          strokeDasharray={CIRCUMFERENCE}
          strokeDashoffset={offset}
          transform="rotate(-90 40 40)"
          style={{ transition: "stroke-dashoffset 300ms ease" }}
        />
      </svg>
      <p className="jetson-gauge__value">
        {value.toFixed(unit === "%" ? 0 : 1)}
        {unit}
      </p>
      <p className="jetson-gauge__label">{label}</p>
    </div>
  );
}

export function JetsonMetricsPanel() {
  const [metrics, setMetrics] = useState<JetsonMetrics | null>(null);

  useEffect(() => {
    let mounted = true;

    const poll = () => {
      getJetsonMetrics().then((data) => {
        if (mounted) setMetrics(data);
      });
    };

    poll();
    const id = setInterval(poll, 3000);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <Panel
      eyebrow="Hardware"
      title="Jetson Orin NX"
      action={<Cpu size={20} strokeWidth={1.8} color="var(--ink-muted)" />}
    >
      {metrics ? (
        <div className="jetson-grid">
          <GaugeCard
            label="CPU"
            value={metrics.cpuPercent}
            max={100}
            unit="%"
            thresholds={PCT_THRESHOLDS}
          />
          <GaugeCard
            label="RAM"
            value={metrics.ramPercent}
            max={100}
            unit="%"
            thresholds={PCT_THRESHOLDS}
          />
          <GaugeCard
            label="GPU Temp"
            value={metrics.gpuTempCelsius}
            max={90}
            unit="°C"
            thresholds={TEMP_THRESHOLDS}
          />
          <GaugeCard
            label="CPU Temp"
            value={metrics.cpuTempCelsius}
            max={90}
            unit="°C"
            thresholds={TEMP_THRESHOLDS}
          />
        </div>
      ) : (
        <div className="jetson-grid jetson-grid--loading">
          {[0, 1, 2, 3].map((i) => (
            <div key={i} className="jetson-gauge jetson-gauge--skeleton" />
          ))}
        </div>
      )}
    </Panel>
  );
}
