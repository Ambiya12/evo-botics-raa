import type { JetsonMetrics } from "../types/admin";
import { createMockJetsonMetricsProvider } from "./providers/mockJetsonMetricsProvider";
import type { JetsonMetricsProvider } from "./providers/jetsonMetricsProvider";

const defaultProvider: JetsonMetricsProvider = createMockJetsonMetricsProvider();

let provider: JetsonMetricsProvider = defaultProvider;

export function setJetsonMetricsProvider(nextProvider: JetsonMetricsProvider): void {
  provider = nextProvider;
}

export function resetJetsonMetricsProvider(): void {
  provider = defaultProvider;
}

export async function getJetsonMetrics(): Promise<JetsonMetrics> {
  return provider.fetchJetsonMetrics();
}
