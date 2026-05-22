import { jetsonMetrics as seedJetsonMetrics } from "../../data/mockAdminData";
import type { JetsonMetrics } from "../../types/admin";
import type { JetsonMetricsProvider } from "./jetsonMetricsProvider";

export function createMockJetsonMetricsProvider(
  initialJetsonMetrics: JetsonMetrics = seedJetsonMetrics,
): JetsonMetricsProvider {
  const store: JetsonMetrics = structuredClone(initialJetsonMetrics);

  return {
    async fetchJetsonMetrics() {
      return Promise.resolve(structuredClone(store));
    },
  };
}
