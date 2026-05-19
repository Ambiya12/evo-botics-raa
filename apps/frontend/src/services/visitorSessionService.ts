import { currentSession } from "../data/mockAdminData";
import type { VisitorSession } from "../types/admin";

export interface VisitorSessionProvider {
  fetchCurrentSession: () => Promise<VisitorSession | null>;
}

const mockVisitorSessionProvider: VisitorSessionProvider = {
  async fetchCurrentSession() {
    return Promise.resolve(structuredClone(currentSession));
  },
};

let provider: VisitorSessionProvider = mockVisitorSessionProvider;

export function setVisitorSessionProvider(nextProvider: VisitorSessionProvider): void {
  provider = nextProvider;
}

export async function getCurrentVisitorSession(): Promise<VisitorSession | null> {
  return provider.fetchCurrentSession();
}
