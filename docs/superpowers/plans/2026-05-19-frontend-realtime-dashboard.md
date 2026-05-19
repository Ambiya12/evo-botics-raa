# Frontend Dashboard Temps Réel — Plan d'implémentation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connecter le dashboard admin aux données réelles du robot via WebSocket (Laravel Reverb) et ajouter des graphiques de séries temporelles (batterie, état navigation, latence) persistés dans IndexedDB.

**Architecture:** Le provider pattern existant est le point d'entrée : `createLaravelEchoRobotDataProvider` remplace `mockRobotDataProvider` quand les variables d'environnement Reverb sont définies. Les métriques reçues par WebSocket sont écrites dans IndexedDB (Dexie.js) avec pruning automatique à 24h. Trois graphiques Recharts sont ajoutés dans un nouveau `TimeSeriesPanel`.

**Tech Stack:** laravel-echo + pusher-js (WebSocket), dexie + dexie-react-hooks (IndexedDB), recharts (graphiques), vitest + jsdom + fake-indexeddb (tests)

**Spec de référence:** `docs/superpowers/specs/2026-05-19-frontend-realtime-dashboard-design.md`

---

## File Map

```
NOUVEAUX
apps/frontend/src/services/providers/websocketConnectionManager.ts
apps/frontend/src/services/providers/connectionManagerStore.ts
apps/frontend/src/services/providers/laravelEchoRobotDataProvider.ts
apps/frontend/src/services/providers/laravelEchoVisitorSessionProvider.ts
apps/frontend/src/services/providers/laravelEchoEventLogProvider.ts
apps/frontend/src/services/providers/laravelEchoIncidentProvider.ts
apps/frontend/src/services/timeSeriesStore.ts
apps/frontend/src/hooks/useTimeSeriesData.ts
apps/frontend/src/components/admin/TimeSeriesPanel.tsx
apps/frontend/src/test/setup.ts
apps/frontend/.env.example

MODIFIÉS
apps/frontend/vite.config.ts              — ajout config vitest
apps/frontend/package.json                — ajout scripts test + deps
apps/frontend/src/types/admin.ts          — +2 états ConnectionStatus
apps/frontend/src/constants/adminLabels.ts— +2 entrées connectionLabel + connectionTone
apps/frontend/src/hooks/useDashboardData.ts — expose connectionStatus
apps/frontend/src/components/admin/Topbar.tsx   — affiche connectionStatus badge
apps/frontend/src/components/admin/AdminShell.tsx — passe connectionStatus
apps/frontend/src/app/AdminDashboard.tsx  — passe connectionStatus + ajoute TimeSeriesPanel
apps/frontend/src/main.tsx                — init providers si env Reverb défini
```

---

### Task 1 : Installer les dépendances et configurer Vitest

**Files:**
- Modify: `apps/frontend/package.json` (via npm)
- Modify: `apps/frontend/vite.config.ts`
- Create: `apps/frontend/src/test/setup.ts`

- [ ] **Step 1 : Installer les dépendances runtime**

Depuis `apps/frontend/` :
```bash
npm install laravel-echo pusher-js dexie dexie-react-hooks recharts
```

Expected : no errors, packages appear in `node_modules/`

- [ ] **Step 2 : Installer les dépendances de test**

```bash
npm install --save-dev vitest @vitest/coverage-v8 jsdom @testing-library/react @testing-library/user-event fake-indexeddb
```

- [ ] **Step 3 : Ajouter les scripts test dans package.json**

Modifier la section `scripts` de `apps/frontend/package.json` :
```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview",
    "lint": "eslint .",
    "test": "vitest run",
    "test:watch": "vitest"
  }
}
```

- [ ] **Step 4 : Configurer Vitest dans vite.config.ts**

```typescript
// apps/frontend/vite.config.ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
```

- [ ] **Step 5 : Créer le fichier de setup de test**

```typescript
// apps/frontend/src/test/setup.ts
// Global test environment setup — extend here as needed
```

- [ ] **Step 6 : Vérifier que Vitest fonctionne**

```bash
cd apps/frontend && npm test 2>&1 | head -10
```

Expected : `No test files found, exiting with code 0` ou similar — pas d'erreur de config

- [ ] **Step 7 : Commit**

```bash
git add apps/frontend/package.json apps/frontend/package-lock.json apps/frontend/vite.config.ts apps/frontend/src/test/setup.ts
git commit -m "chore(frontend): add vitest + websocket + timeseries dependencies"
```

---

### Task 2 : Étendre ConnectionStatus et mettre à jour adminLabels

**Files:**
- Modify: `apps/frontend/src/types/admin.ts`
- Modify: `apps/frontend/src/constants/adminLabels.ts`
- Create: `apps/frontend/src/types/__tests__/admin.test.ts`

- [ ] **Step 1 : Écrire le test (il va échouer car les valeurs n'existent pas encore)**

```typescript
// apps/frontend/src/types/__tests__/admin.test.ts
import { describe, it, expect } from "vitest";
import type { ConnectionStatus } from "../admin";

describe("ConnectionStatus", () => {
  it("includes the 5 expected states", () => {
    const states: ConnectionStatus[] = [
      "mock",
      "connecting",
      "connected_ros",
      "disconnected",
      "error",
    ];
    expect(states).toHaveLength(5);
  });
});
```

```bash
cd apps/frontend && npm test -- src/types/__tests__/admin.test.ts
```

Expected : FAIL — `"connecting"` et `"error"` ne sont pas des valeurs valides

- [ ] **Step 2 : Modifier le type ConnectionStatus dans admin.ts**

Dans `apps/frontend/src/types/admin.ts`, remplacer la ligne :
```typescript
// Avant
export type ConnectionStatus = "mock" | "disconnected" | "connected_ros";

// Après
export type ConnectionStatus = "mock" | "connecting" | "connected_ros" | "disconnected" | "error";
```

- [ ] **Step 3 : Mettre à jour adminLabels.ts**

Dans `apps/frontend/src/constants/adminLabels.ts`, remplacer les deux records `connectionLabel` et `connectionTone` :

```typescript
export const connectionLabel: Record<ConnectionStatus, string> = {
  mock: "Mock mode",
  connecting: "Connecting...",
  connected_ros: "ROS connected",
  disconnected: "Disconnected",
  error: "Connection error",
};

export const connectionTone: Record<ConnectionStatus, BadgeTone> = {
  mock: "muted",
  connecting: "warning",
  connected_ros: "success",
  disconnected: "danger",
  error: "danger",
};
```

- [ ] **Step 4 : Lancer le test**

```bash
npm test -- src/types/__tests__/admin.test.ts
```

Expected : PASS

- [ ] **Step 5 : Vérifier qu'il n'y a pas d'erreur TypeScript**

```bash
npm run build 2>&1 | head -20
```

Expected : no new errors

- [ ] **Step 6 : Commit**

```bash
git add apps/frontend/src/types/admin.ts apps/frontend/src/types/__tests__/admin.test.ts apps/frontend/src/constants/adminLabels.ts
git commit -m "feat(frontend): extend ConnectionStatus with connecting and error states"
```

---

### Task 3 : Créer le timeSeriesStore (IndexedDB)

**Files:**
- Create: `apps/frontend/src/services/timeSeriesStore.ts`
- Create: `apps/frontend/src/services/__tests__/timeSeriesStore.test.ts`

- [ ] **Step 1 : Écrire les tests**

```typescript
// apps/frontend/src/services/__tests__/timeSeriesStore.test.ts
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
```

```bash
cd apps/frontend && npm test -- src/services/__tests__/timeSeriesStore.test.ts
```

Expected : FAIL — `timeSeriesStore` module not found

- [ ] **Step 2 : Implémenter timeSeriesStore.ts**

```typescript
// apps/frontend/src/services/timeSeriesStore.ts
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
```

- [ ] **Step 3 : Lancer les tests**

```bash
npm test -- src/services/__tests__/timeSeriesStore.test.ts
```

Expected : 5 tests PASS

- [ ] **Step 4 : Commit**

```bash
git add apps/frontend/src/services/timeSeriesStore.ts apps/frontend/src/services/__tests__/timeSeriesStore.test.ts
git commit -m "feat(frontend): add IndexedDB time series store with 24h retention"
```

---

### Task 4 : Créer le hook useTimeSeriesData

**Files:**
- Create: `apps/frontend/src/hooks/useTimeSeriesData.ts`
- Create: `apps/frontend/src/hooks/__tests__/useTimeSeriesData.test.ts`

- [ ] **Step 1 : Écrire les tests**

```typescript
// apps/frontend/src/hooks/__tests__/useTimeSeriesData.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import "fake-indexeddb/auto";
import { db } from "../../services/timeSeriesStore";
import { useTimeSeriesData } from "../useTimeSeriesData";

beforeEach(async () => {
  await db.metrics.clear();
});

describe("useTimeSeriesData", () => {
  it("returns empty array when no data exists", () => {
    const { result } = renderHook(() => useTimeSeriesData("battery", 15));
    expect(result.current).toEqual([]);
  });

  it("returns only points within the given window", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 1_000, metric: "battery", value: 80 },
      { timestamp: now - 30 * 60 * 1000, metric: "battery", value: 60 },
    ]);
    const { result } = renderHook(() => useTimeSeriesData("battery", 15));
    await waitFor(() => {
      expect(result.current).toHaveLength(1);
    });
    expect(result.current[0].value).toBe(80);
  });

  it("does not return points from another metric", async () => {
    const now = Date.now();
    await db.metrics.bulkAdd([
      { timestamp: now - 1_000, metric: "latency", value: 42 },
    ]);
    const { result } = renderHook(() => useTimeSeriesData("battery", 15));
    await waitFor(() => {
      expect(result.current).toHaveLength(0);
    });
  });
});
```

```bash
cd apps/frontend && npm test -- src/hooks/__tests__/useTimeSeriesData.test.ts
```

Expected : FAIL — module not found

- [ ] **Step 2 : Implémenter useTimeSeriesData.ts**

```typescript
// apps/frontend/src/hooks/useTimeSeriesData.ts
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
```

- [ ] **Step 3 : Lancer les tests**

```bash
npm test -- src/hooks/__tests__/useTimeSeriesData.test.ts
```

Expected : 3 tests PASS

- [ ] **Step 4 : Commit**

```bash
git add apps/frontend/src/hooks/useTimeSeriesData.ts apps/frontend/src/hooks/__tests__/useTimeSeriesData.test.ts
git commit -m "feat(frontend): add useTimeSeriesData hook with live IndexedDB queries"
```

---

### Task 5 : Créer websocketConnectionManager et connectionManagerStore

**Files:**
- Create: `apps/frontend/src/services/providers/websocketConnectionManager.ts`
- Create: `apps/frontend/src/services/providers/connectionManagerStore.ts`

- [ ] **Step 1 : Implémenter websocketConnectionManager.ts**

```typescript
// apps/frontend/src/services/providers/websocketConnectionManager.ts
import Echo from "laravel-echo";
import Pusher from "pusher-js";
import type { ConnectionStatus } from "../../types/admin";

declare global {
  interface Window {
    Pusher: typeof Pusher;
  }
}

type StatusListener = (status: ConnectionStatus) => void;

export interface WebSocketConnectionManager {
  readonly echo: Echo;
  readonly status: ConnectionStatus;
  subscribe(listener: StatusListener): () => void;
  destroy(): void;
}

export function createWebSocketConnectionManager(
  wsUrl: string,
  appKey: string,
): WebSocketConnectionManager {
  window.Pusher = Pusher;

  const url = new URL(wsUrl);
  const isTls = url.protocol === "wss:";

  const echo = new Echo({
    broadcaster: "reverb",
    key: appKey,
    wsHost: url.hostname,
    wsPort: isTls ? undefined : Number(url.port) || 80,
    wssPort: isTls ? Number(url.port) || 443 : undefined,
    forceTLS: isTls,
    enabledTransports: ["ws", "wss"],
  });

  let currentStatus: ConnectionStatus = "connecting";
  const listeners = new Set<StatusListener>();

  function notify(next: ConnectionStatus): void {
    currentStatus = next;
    for (const fn of listeners) fn(next);
  }

  const pusher = echo.connector.pusher;
  let retryCount = 0;

  pusher.connection.bind("connected", () => {
    retryCount = 0;
    notify("connected_ros");
  });
  pusher.connection.bind("disconnected", () => notify("disconnected"));
  pusher.connection.bind("error", () => notify("error"));
  pusher.connection.bind("unavailable", () => {
    notify("disconnected");
    const delay = Math.min(1_000 * 2 ** retryCount, 30_000);
    retryCount++;
    setTimeout(() => pusher.connection.connect(), delay);
  });

  return {
    get echo() {
      return echo;
    },
    get status() {
      return currentStatus;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    destroy() {
      echo.disconnect();
      listeners.clear();
    },
  };
}
```

- [ ] **Step 2 : Implémenter connectionManagerStore.ts**

Ce module sert de pont entre `main.tsx` (qui crée le manager) et `useDashboardData` (qui consomme le statut).

```typescript
// apps/frontend/src/services/providers/connectionManagerStore.ts
import type { ConnectionStatus } from "../../types/admin";

type StatusListener = (status: ConnectionStatus) => void;

let currentStatus: ConnectionStatus = "mock";
const listeners = new Set<StatusListener>();

export function setConnectionManagerStatus(status: ConnectionStatus): void {
  currentStatus = status;
  for (const fn of listeners) fn(status);
}

export function getConnectionManagerStatus(): ConnectionStatus {
  return currentStatus;
}

export function subscribeConnectionStatus(
  listener: StatusListener,
): () => void {
  listeners.add(listener);
  listener(currentStatus);
  return () => listeners.delete(listener);
}
```

- [ ] **Step 3 : Vérifier la compilation**

```bash
cd apps/frontend && npm run build 2>&1 | head -20
```

Expected : no errors

- [ ] **Step 4 : Commit**

```bash
git add apps/frontend/src/services/providers/websocketConnectionManager.ts apps/frontend/src/services/providers/connectionManagerStore.ts
git commit -m "feat(frontend): add websocket connection manager and connection status store"
```

---

### Task 6 : Créer laravelEchoRobotDataProvider

**Files:**
- Create: `apps/frontend/src/services/providers/laravelEchoRobotDataProvider.ts`
- Create: `apps/frontend/src/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts`

- [ ] **Step 1 : Écrire les tests**

```typescript
// apps/frontend/src/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts
import { describe, it, expect, vi, beforeEach } from "vitest";
import "fake-indexeddb/auto";
import { db } from "../../timeSeriesStore";

vi.mock("laravel-echo", () => ({ default: vi.fn() }));
vi.mock("pusher-js", () => ({ default: vi.fn() }));

import { createLaravelEchoRobotDataProvider } from "../laravelEchoRobotDataProvider";
import type { WebSocketConnectionManager } from "../websocketConnectionManager";
import type { RobotStatus } from "../../../types/admin";

type EventHandler = (data: unknown) => void;

function makeManager(): {
  manager: WebSocketConnectionManager;
  emit: (event: string, data: unknown) => void;
} {
  const handlers: Record<string, EventHandler> = {};
  const channelMock = {
    listen: vi.fn().mockImplementation((event: string, handler: EventHandler) => {
      handlers[event] = handler;
      return channelMock;
    }),
  };
  const manager: WebSocketConnectionManager = {
    echo: {
      channel: vi.fn().mockReturnValue(channelMock),
      connector: { pusher: { channel: vi.fn().mockReturnValue(null) } },
    } as unknown as WebSocketConnectionManager["echo"],
    status: "connected_ros",
    subscribe: vi.fn(),
    destroy: vi.fn(),
  };
  return {
    manager,
    emit: (event, data) => handlers[event]?.(data),
  };
}

const baseMessage: RobotStatus & { sentAt: string } = {
  id: "r1",
  name: "Robot",
  mode: "rosbridge",
  connectionStatus: "connected_ros",
  state: "GUIDING",
  battery: 80,
  location: "Hall",
  currentWaypoint: "wp-01",
  destination: "Room B",
  currentMissionSessionId: null,
  lastIncidentSummary: "",
  lastUpdate: "10:00:00",
  emergencyStop: false,
  services: [],
  sentAt: new Date().toISOString(),
};

beforeEach(async () => {
  await db.metrics.clear();
});

describe("createLaravelEchoRobotDataProvider", () => {
  it("rejects fetchRobotStatus before first WebSocket message", async () => {
    const { manager } = makeManager();
    const provider = createLaravelEchoRobotDataProvider(manager);
    await expect(provider.fetchRobotStatus()).rejects.toThrow(
      "No robot status received yet",
    );
  });

  it("returns cached status after receiving RobotStatusUpdated", async () => {
    const { manager, emit } = makeManager();
    const provider = createLaravelEchoRobotDataProvider(manager);
    emit("RobotStatusUpdated", baseMessage);
    const status = await provider.fetchRobotStatus();
    expect(status.battery).toBe(80);
  });

  it("does not expose sentAt on the returned status", async () => {
    const { manager, emit } = makeManager();
    const provider = createLaravelEchoRobotDataProvider(manager);
    emit("RobotStatusUpdated", baseMessage);
    const status = await provider.fetchRobotStatus();
    expect((status as Record<string, unknown>)["sentAt"]).toBeUndefined();
  });

  it("writes 3 metric points to IndexedDB on each update", async () => {
    const { manager, emit } = makeManager();
    createLaravelEchoRobotDataProvider(manager);
    emit("RobotStatusUpdated", baseMessage);
    await new Promise((r) => setTimeout(r, 50));
    const points = await db.metrics.toArray();
    expect(points).toHaveLength(3);
  });
});
```

```bash
cd apps/frontend && npm test -- src/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts
```

Expected : FAIL — module not found

- [ ] **Step 2 : Implémenter laravelEchoRobotDataProvider.ts**

```typescript
// apps/frontend/src/services/providers/laravelEchoRobotDataProvider.ts
import type { RobotStatus } from "../../types/admin";
import type { RobotStatusProvider } from "./robotStatusProvider";
import { appendMetricPoints } from "../timeSeriesStore";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

type RobotStatusMessage = RobotStatus & { sentAt: string };

export function createLaravelEchoRobotDataProvider(
  manager: WebSocketConnectionManager,
): RobotStatusProvider {
  let cache: RobotStatus | null = null;

  manager.echo
    .channel("robot-dashboard")
    .listen("RobotStatusUpdated", (data: RobotStatusMessage) => {
      const { sentAt, ...robotStatus } = data;
      cache = robotStatus as RobotStatus;
      const latency = Date.now() - new Date(sentAt).getTime();
      void appendMetricPoints(cache, latency);
    });

  return {
    async fetchRobotStatus() {
      if (!cache) {
        throw new Error("No robot status received yet");
      }
      return structuredClone(cache);
    },

    async setEmergencyStopState(isActive) {
      // Requires client events on private-robot-dashboard channel in Reverb config
      // Coordinate with backend team to enable client events
      const channel = manager.echo.connector.pusher.channel("private-robot-dashboard");
      if (channel?.trigger) {
        channel.trigger("client-EmergencyStopRequested", { isActive });
      }
      return Promise.resolve();
    },
  };
}
```

- [ ] **Step 3 : Lancer les tests**

```bash
npm test -- src/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts
```

Expected : 4 tests PASS

- [ ] **Step 4 : Commit**

```bash
git add apps/frontend/src/services/providers/laravelEchoRobotDataProvider.ts apps/frontend/src/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts
git commit -m "feat(frontend): add Laravel Echo robot data provider with time series ingestion"
```

---

### Task 7 : Créer les providers WebSocket pour les autres services

**Files:**
- Create: `apps/frontend/src/services/providers/laravelEchoVisitorSessionProvider.ts`
- Create: `apps/frontend/src/services/providers/laravelEchoEventLogProvider.ts`
- Create: `apps/frontend/src/services/providers/laravelEchoIncidentProvider.ts`

- [ ] **Step 1 : Implémenter laravelEchoVisitorSessionProvider.ts**

```typescript
// apps/frontend/src/services/providers/laravelEchoVisitorSessionProvider.ts
import type { VisitorSession } from "../../types/admin";
import type { VisitorSessionProvider } from "../visitorSessionService";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

export function createLaravelEchoVisitorSessionProvider(
  manager: WebSocketConnectionManager,
): VisitorSessionProvider {
  let cache: VisitorSession | null = null;

  manager.echo
    .channel("robot-dashboard")
    .listen("VisitorSessionUpdated", (data: VisitorSession) => {
      cache = data;
    });

  return {
    async fetchCurrentSession() {
      return cache ? structuredClone(cache) : null;
    },
  };
}
```

- [ ] **Step 2 : Implémenter laravelEchoEventLogProvider.ts**

```typescript
// apps/frontend/src/services/providers/laravelEchoEventLogProvider.ts
import type { EventLog } from "../../types/admin";
import type { EventLogProvider } from "../eventLogService";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

const MAX_LOGS = 200;

export function createLaravelEchoEventLogProvider(
  manager: WebSocketConnectionManager,
): EventLogProvider {
  const cache: EventLog[] = [];

  manager.echo
    .channel("robot-dashboard")
    .listen("EventLogCreated", (data: EventLog) => {
      cache.unshift(data);
      if (cache.length > MAX_LOGS) cache.pop();
    });

  return {
    async fetchRecentEventLogs() {
      return structuredClone(cache);
    },
  };
}
```

- [ ] **Step 3 : Implémenter laravelEchoIncidentProvider.ts**

```typescript
// apps/frontend/src/services/providers/laravelEchoIncidentProvider.ts
import type { Incident } from "../../types/admin";
import type { IncidentProvider } from "../incidentService";
import type { WebSocketConnectionManager } from "./websocketConnectionManager";

export function createLaravelEchoIncidentProvider(
  manager: WebSocketConnectionManager,
): IncidentProvider {
  let cache: Incident[] = [];

  manager.echo
    .channel("robot-dashboard")
    .listen("IncidentUpdated", (data: Incident) => {
      const exists = cache.some((i) => i.id === data.id);
      cache = exists
        ? cache.map((i) => (i.id === data.id ? data : i))
        : [data, ...cache];
    });

  return {
    async fetchIncidents() {
      return structuredClone(cache);
    },

    async acknowledgeIncident(incidentId) {
      // Requires client events on private-robot-dashboard channel in Reverb config
      const channel = manager.echo.connector.pusher.channel("private-robot-dashboard");
      if (channel?.trigger) {
        channel.trigger("client-IncidentAcknowledged", { incidentId });
      }
      return Promise.resolve();
    },
  };
}
```

- [ ] **Step 4 : Vérifier la compilation**

```bash
cd apps/frontend && npm run build 2>&1 | head -20
```

Expected : no errors

- [ ] **Step 5 : Commit**

```bash
git add apps/frontend/src/services/providers/laravelEchoVisitorSessionProvider.ts apps/frontend/src/services/providers/laravelEchoEventLogProvider.ts apps/frontend/src/services/providers/laravelEchoIncidentProvider.ts
git commit -m "feat(frontend): add Laravel Echo providers for session, event logs and incidents"
```

---

### Task 8 : Brancher les providers dans main.tsx

**Files:**
- Modify: `apps/frontend/src/main.tsx`
- Create: `apps/frontend/.env.example`

- [ ] **Step 1 : Créer .env.example**

```
# apps/frontend/.env.example
# Copier en .env.local et remplir avec les valeurs du dev backend
VITE_REVERB_URL=ws://10.10.221.115:6001
VITE_REVERB_APP_KEY=your-reverb-app-key
```

Port par défaut de Laravel Reverb : **6001** (à confirmer avec le dev backend).

- [ ] **Step 2 : Remplacer le contenu de main.tsx**

```typescript
// apps/frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { AdminDashboard } from "./app/AdminDashboard";
import { pruneOldMetrics } from "./services/timeSeriesStore";
import "./styles.css";

async function bootstrap(): Promise<void> {
  await pruneOldMetrics();

  const reverbUrl = import.meta.env.VITE_REVERB_URL as string | undefined;
  const reverbKey = import.meta.env.VITE_REVERB_APP_KEY as string | undefined;

  if (reverbUrl && reverbKey) {
    const [
      { createWebSocketConnectionManager },
      { createLaravelEchoRobotDataProvider },
      { createLaravelEchoVisitorSessionProvider },
      { createLaravelEchoEventLogProvider },
      { createLaravelEchoIncidentProvider },
      { setRobotStatusProvider },
      { setVisitorSessionProvider },
      { setEventLogProvider },
      { setIncidentProvider },
      { setConnectionManagerStatus },
    ] = await Promise.all([
      import("./services/providers/websocketConnectionManager"),
      import("./services/providers/laravelEchoRobotDataProvider"),
      import("./services/providers/laravelEchoVisitorSessionProvider"),
      import("./services/providers/laravelEchoEventLogProvider"),
      import("./services/providers/laravelEchoIncidentProvider"),
      import("./services/robotStatusService"),
      import("./services/visitorSessionService"),
      import("./services/eventLogService"),
      import("./services/incidentService"),
      import("./services/providers/connectionManagerStore"),
    ]);

    const manager = createWebSocketConnectionManager(reverbUrl, reverbKey);
    manager.subscribe((status) => setConnectionManagerStatus(status));
    setConnectionManagerStatus("connecting");

    setRobotStatusProvider(createLaravelEchoRobotDataProvider(manager));
    setVisitorSessionProvider(createLaravelEchoVisitorSessionProvider(manager));
    setEventLogProvider(createLaravelEchoEventLogProvider(manager));
    setIncidentProvider(createLaravelEchoIncidentProvider(manager));
  }

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <AdminDashboard />
    </React.StrictMode>,
  );
}

void bootstrap();
```

- [ ] **Step 3 : Vérifier la compilation**

```bash
cd apps/frontend && npm run build 2>&1 | head -20
```

Expected : no errors

- [ ] **Step 4 : Commit**

```bash
git add apps/frontend/src/main.tsx apps/frontend/.env.example
git commit -m "feat(frontend): bootstrap real WebSocket providers when VITE_REVERB_URL is set"
```

---

### Task 9 : Exposer connectionStatus dans useDashboardData

**Files:**
- Modify: `apps/frontend/src/hooks/useDashboardData.ts`

- [ ] **Step 1 : Modifier useDashboardData.ts**

Ajouter les imports en tête du fichier :
```typescript
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { triggerEmergencyStop } from "../services/adminControlService";
import { getRecentEventLogs } from "../services/eventLogService";
import { acknowledgeIncidentById, getIncidents } from "../services/incidentService";
import { getRobotStatus } from "../services/robotStatusService";
import { getCurrentVisitorSession } from "../services/visitorSessionService";
import {
  getConnectionManagerStatus,
  subscribeConnectionStatus,
} from "../services/providers/connectionManagerStore";
import type { ConnectionStatus, EventLog, Incident, RobotStatus, VisitorSession } from "../types/admin";
```

Ajouter `connectionStatus` dans l'interface `DashboardDataState` :
```typescript
interface DashboardDataState {
  robotStatus: RobotStatus | null;
  currentSession: VisitorSession | null;
  eventLogs: EventLog[];
  incidents: Incident[];
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastSyncedAt: string | null;
}
```

Ajouter un state `connectionStatus` dans le corps du hook, après `const [state, setState] = useState(...)` :
```typescript
const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>(
  getConnectionManagerStatus(),
);
```

Ajouter un `useEffect` pour souscrire aux changements, après le `useEffect` existant :
```typescript
useEffect(() => {
  return subscribeConnectionStatus(setConnectionStatus);
}, []);
```

Ajouter `connectionStatus` dans le `useMemo` final :
```typescript
return useMemo(
  () => ({
    ...state,
    connectionStatus,
    refresh,
    acknowledgeIncident,
    requestEmergencyStop,
  }),
  [acknowledgeIncident, connectionStatus, refresh, requestEmergencyStop, state],
);
```

- [ ] **Step 2 : Vérifier la compilation**

```bash
cd apps/frontend && npm run build 2>&1 | head -20
```

Expected : no errors

- [ ] **Step 3 : Commit**

```bash
git add apps/frontend/src/hooks/useDashboardData.ts
git commit -m "feat(frontend): expose connectionStatus in useDashboardData"
```

---

### Task 10 : Afficher le badge de connexion dans Topbar

**Files:**
- Modify: `apps/frontend/src/components/admin/Topbar.tsx`
- Modify: `apps/frontend/src/components/admin/AdminShell.tsx`
- Modify: `apps/frontend/src/app/AdminDashboard.tsx`

- [ ] **Step 1 : Modifier Topbar.tsx**

Remplacer le contenu complet :
```tsx
// apps/frontend/src/components/admin/Topbar.tsx
import { Bell, RefreshCw, Search } from "lucide-react";
import { StatusBadge } from "../ui/StatusBadge";
import { connectionLabel, connectionTone } from "../../constants/adminLabels";
import type { ConnectionStatus } from "../../types/admin";

interface TopbarProps {
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  lastSyncedAt: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  connectionStatus: ConnectionStatus;
}

export function Topbar({
  searchQuery,
  onSearchQueryChange,
  lastSyncedAt,
  isRefreshing,
  onRefresh,
  connectionStatus,
}: TopbarProps) {
  return (
    <header className="topbar">
      <div>
        <p className="section-kicker">Operator console</p>
        <h2>Robot monitoring dashboard</h2>
        <p className="topbar__meta">
          {lastSyncedAt ? `Last synced ${lastSyncedAt}` : "Preparing live telemetry"}
        </p>
        <StatusBadge
          label={connectionLabel[connectionStatus]}
          tone={connectionTone[connectionStatus]}
        />
      </div>

      <div className="topbar__actions">
        <label className="search" htmlFor="dashboard-search">
          <Search aria-hidden="true" size={17} strokeWidth={1.8} />
          <input
            id="dashboard-search"
            placeholder="Filter events and incidents"
            type="search"
            value={searchQuery}
            onChange={(event) => onSearchQueryChange(event.target.value)}
          />
        </label>
        <button
          className="icon-button"
          type="button"
          aria-label="Refresh dashboard data"
          onClick={onRefresh}
          disabled={isRefreshing}
        >
          <RefreshCw
            aria-hidden="true"
            size={18}
            className={isRefreshing ? "spin" : ""}
          />
        </button>
        <button
          className="icon-button"
          type="button"
          aria-label="Open notifications"
        >
          <Bell aria-hidden="true" size={18} />
        </button>
      </div>
    </header>
  );
}
```

- [ ] **Step 2 : Modifier AdminShell.tsx pour passer connectionStatus**

```tsx
// apps/frontend/src/components/admin/AdminShell.tsx
import type { ReactNode } from "react";
import type { ConnectionStatus } from "../../types/admin";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";

interface AdminShellProps {
  children: ReactNode;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  lastSyncedAt: string | null;
  isRefreshing: boolean;
  onRefresh: () => void;
  connectionStatus: ConnectionStatus;
}

export function AdminShell({
  children,
  searchQuery,
  onSearchQueryChange,
  lastSyncedAt,
  isRefreshing,
  onRefresh,
  connectionStatus,
}: AdminShellProps) {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="dashboard">
        <Topbar
          searchQuery={searchQuery}
          onSearchQueryChange={onSearchQueryChange}
          lastSyncedAt={lastSyncedAt}
          isRefreshing={isRefreshing}
          onRefresh={onRefresh}
          connectionStatus={connectionStatus}
        />
        {children}
      </main>
    </div>
  );
}
```

- [ ] **Step 3 : Modifier AdminDashboard.tsx pour passer connectionStatus**

Dans `AdminDashboard.tsx`, déstructurer `connectionStatus` depuis `useDashboardData()` :
```typescript
const {
  robotStatus,
  currentSession,
  eventLogs,
  incidents,
  isLoading,
  isRefreshing,
  error,
  lastSyncedAt,
  connectionStatus,
  refresh,
  acknowledgeIncident,
  requestEmergencyStop,
} = useDashboardData();
```

Passer `connectionStatus` à `AdminShell` :
```tsx
<AdminShell
  searchQuery={searchQuery}
  onSearchQueryChange={setSearchQuery}
  lastSyncedAt={lastSyncedAt}
  isRefreshing={isRefreshing}
  onRefresh={() => { void refresh(); }}
  connectionStatus={connectionStatus}
>
```

- [ ] **Step 4 : Vérifier la compilation**

```bash
cd apps/frontend && npm run build 2>&1 | head -20
```

Expected : no errors

- [ ] **Step 5 : Démarrer le dev server et vérifier visuellement le badge**

```bash
npm run dev
```

Ouvrir `http://localhost:5173` — vérifier que le badge "Mock mode" apparaît sous le titre du dashboard.

- [ ] **Step 6 : Commit**

```bash
git add apps/frontend/src/components/admin/Topbar.tsx apps/frontend/src/components/admin/AdminShell.tsx apps/frontend/src/app/AdminDashboard.tsx
git commit -m "feat(frontend): display WebSocket connection status badge in Topbar"
```

---

### Task 11 : Créer le TimeSeriesPanel

**Files:**
- Create: `apps/frontend/src/components/admin/TimeSeriesPanel.tsx`

- [ ] **Step 1 : Implémenter TimeSeriesPanel.tsx**

```tsx
// apps/frontend/src/components/admin/TimeSeriesPanel.tsx
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
          labelFormatter={(ts: number) =>
            new Date(ts).toLocaleTimeString()
          }
          formatter={(value: number) => [
            tooltipFormatter ? tooltipFormatter(value) : String(value),
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
```

- [ ] **Step 2 : Vérifier la compilation TypeScript**

```bash
cd apps/frontend && npm run build 2>&1 | head -20
```

Expected : no errors

- [ ] **Step 3 : Commit**

```bash
git add apps/frontend/src/components/admin/TimeSeriesPanel.tsx
git commit -m "feat(frontend): add TimeSeriesPanel with battery, nav state and latency charts"
```

---

### Task 12 : Intégrer TimeSeriesPanel dans AdminDashboard

**Files:**
- Modify: `apps/frontend/src/app/AdminDashboard.tsx`

- [ ] **Step 1 : Ajouter l'import de TimeSeriesPanel**

Dans `apps/frontend/src/app/AdminDashboard.tsx`, ajouter l'import :
```typescript
import { TimeSeriesPanel } from "../components/admin/TimeSeriesPanel";
```

- [ ] **Step 2 : Ajouter TimeSeriesPanel dans le rendu**

Dans le bloc JSX qui suit `<RobotStatusOverview>`, ajouter `<TimeSeriesPanel />` juste avant la `dashboard-grid` :
```tsx
<>
  <RobotStatusOverview robotStatus={robotStatus} />
  <TimeSeriesPanel />
  <div className="dashboard-grid">
    <RobotHealthPanel robotStatus={robotStatus} />
    <CurrentVisitorSessionPanel session={currentSession} />
    <SafetyActions
      emergencyStopActive={robotStatus.emergencyStop}
      onEmergencyStop={requestEmergencyStop}
    />
    <EventLogTable logs={filteredLogs} />
    <IncidentMonitoringPanel
      incidents={filteredIncidents}
      onAcknowledge={acknowledgeIncident}
    />
  </div>
</>
```

- [ ] **Step 3 : Démarrer le dev server et vérifier visuellement**

```bash
cd apps/frontend && npm run dev
```

Ouvrir `http://localhost:5173`. Vérifier que :
- Le panel "Time series" apparaît sous `RobotStatusOverview`
- Les 3 sous-sections "Battery", "Navigation state", "Latency" sont visibles
- Le message "No data — waiting for robot connection" s'affiche (normal en mock)
- Les boutons 15 min / 1h / 24h sont cliquables
- Les panneaux existants sont intacts

- [ ] **Step 4 : Lancer le build final**

```bash
npm run build
```

Expected : build réussi sans erreurs

- [ ] **Step 5 : Lancer tous les tests**

```bash
npm test
```

Expected : tous les tests PASS

- [ ] **Step 6 : Commit final**

```bash
git add apps/frontend/src/app/AdminDashboard.tsx
git commit -m "feat(frontend): integrate TimeSeriesPanel into admin dashboard"
```

---

## Notes d'intégration pour le dev backend

Ces points sont **bloquants** pour passer du mock au réel et doivent être coordonnés :

1. **Port Reverb** : confirmer le port (défaut Laravel Reverb = 6001) et l'`APP_KEY` pour `.env.local`
2. **Format `sentAt`** : chaque event WebSocket doit inclure `sentAt: string` (ISO 8601) au niveau racine du payload — nécessaire pour le calcul de latence
3. **Client events** (arrêt urgence + acknowledge incident) : activer les client events sur le channel `private-robot-dashboard` dans `config/reverb.php`
4. **Contrats de payload** : les types TypeScript dans `src/types/admin.ts` sont la source de vérité — le backend doit sérialiser exactement ces formes
