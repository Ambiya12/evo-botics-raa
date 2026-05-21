import type { JetsonMetrics } from "../../types/admin";

export interface JetsonMetricsProvider {
  fetchJetsonMetrics: () => Promise<JetsonMetrics>;
}
