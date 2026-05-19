# Spec : Frontend Dashboard Temps Réel — Données Robot

**Date** : 2026-05-19
**Scope** : `apps/frontend` uniquement
**Auteur** : Jules Bourrin
**Statut** : Approuvé

---

## Contexte

Le dashboard admin (`apps/frontend`) est actuellement en mode mock (données simulées statiques). L'objectif est de le connecter aux données réelles du robot via un WebSocket Laravel Reverb, tout en ajoutant des graphiques de séries temporelles pour analyser le comportement du robot dans le temps (batterie, état de navigation, latence).

Le backend (Laravel) est développé par un autre membre de l'équipe. Le robot physique est accessible sur le réseau local (`jetson@10.10.221.115`). L'architecture retenue est : **Robot (ROS2) → Backend Laravel → Frontend React**.

---

## Architecture générale

```
Robot (ROS2 / rosbridge)
        ↓
Backend Laravel + Reverb
        ├── écrit dans InfluxDB (historique long terme, hors scope frontend)
        └── broadcast WebSocket → Frontend
                ↓
LaravelEchoRobotDataProvider
        ↓
Services existants (inchangés)
        ↓
useDashboardData (inchangé)
        ↓
Composants existants (inchangés)
        +
TimeSeriesPanel (nouveau)
```

Le provider pattern déjà en place dans `robotStatusService.ts` (`setRobotStatusProvider()`) est le point d'entrée exact pour ce swap. Aucun composant existant ne change.

---

## Contrats WebSocket (à valider avec le dev backend)

Channel unique : `robot-dashboard`

| Event | Direction | Payload |
|---|---|---|
| `RobotStatusUpdated` | backend → frontend | `RobotStatus` (types/admin.ts) |
| `VisitorSessionUpdated` | backend → frontend | `VisitorSession` (types/admin.ts) |
| `EventLogCreated` | backend → frontend | `EventLog` (types/admin.ts) |
| `IncidentUpdated` | backend → frontend | `Incident` (types/admin.ts) |
| `EmergencyStopRequested` | frontend → backend | `{ isActive: boolean }` |

Les types TypeScript dans `src/types/admin.ts` constituent le contrat partagé. Le backend sérialise ses données dans ces formes exactes.

---

## Section 1 : Provider WebSocket

### `src/services/providers/laravelEchoRobotDataProvider.ts` (nouveau)

Implémente l'interface `RobotStatusProvider` existante. Maintient un cache local du dernier état reçu.

- S'abonne à `robot-dashboard` → `RobotStatusUpdated`
- Met à jour `robotStatusCache` à chaque message reçu
- `fetchRobotStatus()` retourne `robotStatusCache` (pas de requête réseau)
- `setEmergencyStopState(isActive)` émet `EmergencyStopRequested` sur le channel

### `src/services/providers/websocketConnectionManager.ts` (nouveau)

Gère le cycle de vie de l'instance Laravel Echo (singleton partagé).

- États : `connecting | connected | disconnected | error`
- Reconnexion automatique avec backoff exponentiel
- Expose `connectionStatus` pour consommation par `useDashboardData`

### Providers pour les autres services (modifications mineures)

`visitorSessionService.ts`, `eventLogService.ts`, `incidentService.ts` reçoivent chacun :
- Un provider interface (pattern identique à `RobotStatusProvider`)
- Un provider WebSocket correspondant
- Une fonction `setProvider()` pour le swap

### Initialisation dans `main.tsx`

```typescript
if (import.meta.env.MODE === "production") {
  const echo = createLaravelEchoInstance(import.meta.env.VITE_REVERB_URL)
  setRobotStatusProvider(createLaravelEchoRobotDataProvider(echo))
  setVisitorSessionProvider(createLaravelEchoVisitorSessionProvider(echo))
  setEventLogProvider(createLaravelEchoEventLogProvider(echo))
  setIncidentProvider(createLaravelEchoIncidentProvider(echo))
}
// mode mock reste actif par défaut (développement)
```

---

## Section 2 : Historique temps réel (IndexedDB)

### `src/services/timeSeriesStore.ts` (nouveau)

Store Dexie.js avec une table `metrics` :

```typescript
interface MetricPoint {
  id?: number           // auto-increment
  timestamp: number     // Date.now()
  metric: "battery" | "navState" | "latency"
  value: number
}
```

Alimentation : à chaque `RobotStatusUpdated` reçu, 3 points sont écrits :
- `battery` → `robotStatus.battery` (0–100)
- `navState` → index numérique de `robotStatus.state` (IDLE=0, GUIDING=1, ERROR=2, EMERGENCY_STOP=3, autres=4)
- `latency` → delta en ms entre le timestamp ISO du message WebSocket et `Date.now()` — **le backend doit inclure un champ `sentAt: string` (ISO 8601) dans chaque message** ; `robotStatus.lastUpdate` (format `"HH:mm:ss"`) n'est pas parsable en timestamp fiable

Rétention : au démarrage de l'app, suppression automatique des points de plus de 24h. Aucun appel backend.

### `src/hooks/useTimeSeriesData.ts` (nouveau)

```typescript
function useTimeSeriesData(
  metric: "battery" | "navState" | "latency",
  windowMinutes: 15 | 60 | 1440
): MetricPoint[]
```

Réactif via `useLiveQuery` de `dexie-react-hooks` : se met à jour automatiquement à chaque nouvel écrit dans IndexedDB sans polling manuel.

---

## Section 3 : Composant graphiques

### `src/components/admin/TimeSeriesPanel.tsx` (nouveau)

Affiche 3 graphiques via **Recharts** :

| Graphique | Type | Axe Y |
|---|---|---|
| Batterie | `LineChart` | 0–100 % |
| État navigation | `LineChart` (steps) | Labels discrets |
| Latence | `LineChart` | ms |

Fenêtre temporelle sélectionnable : 15 min / 1h / 24h.

Le composant est ajouté dans `AdminDashboard.tsx` comme nouveau panel, sans modifier les panels existants.

---

## Section 4 : Gestion de l'état de connexion

### Modification de `src/types/admin.ts`

```typescript
// Avant
export type ConnectionStatus = "mock" | "disconnected" | "connected_ros"

// Après
export type ConnectionStatus = "mock" | "connecting" | "connected_ros" | "disconnected" | "error"
```

### Affichage dans `Topbar`

| État | Badge |
|---|---|
| `mock` | Gris — "Mode simulation" |
| `connecting` | Jaune animé — "Connexion…" |
| `connected_ros` | Vert — "Robot connecté" |
| `disconnected` | Rouge — "Déconnecté" |
| `error` | Rouge — "Erreur WebSocket" |

`useDashboardData` remonte `connectionStatus` depuis le `websocketConnectionManager`.

---

## Récapitulatif des fichiers

### Nouveaux fichiers

```
src/services/providers/laravelEchoRobotDataProvider.ts
src/services/providers/websocketConnectionManager.ts
src/services/providers/laravelEchoVisitorSessionProvider.ts
src/services/providers/laravelEchoEventLogProvider.ts
src/services/providers/laravelEchoIncidentProvider.ts
src/services/timeSeriesStore.ts
src/hooks/useTimeSeriesData.ts
src/components/admin/TimeSeriesPanel.tsx
```

### Fichiers modifiés

```
src/types/admin.ts                  — ajout états ConnectionStatus
src/services/visitorSessionService.ts — ajout setProvider()
src/services/eventLogService.ts     — ajout setProvider()
src/services/incidentService.ts     — ajout setProvider()
src/hooks/useDashboardData.ts       — ajout connectionStatus
src/components/admin/Topbar.tsx     — affichage connectionStatus
src/app/AdminDashboard.tsx          — ajout TimeSeriesPanel
src/main.tsx                        — init providers selon env
```

### Fichiers inchangés

```
src/services/providers/mockRobotDataProvider.ts
src/services/robotStatusService.ts
src/components/admin/* (tous les panels existants)
src/components/ui/*
```

---

## Dépendances à ajouter

```
laravel-echo          — client WebSocket Laravel/Reverb
pusher-js             — protocole requis par Laravel Echo
dexie                 — wrapper IndexedDB
dexie-react-hooks     — useLiveQuery pour la réactivité React
recharts              — graphiques React
```

---

## Variables d'environnement

```
VITE_REVERB_URL=ws://10.10.221.115:8080   # à confirmer avec le dev backend
VITE_REVERB_APP_KEY=...                    # à confirmer avec le dev backend
```

---

## Ce qui est hors scope

- Backend Laravel (géré séparément)
- InfluxDB (historique long terme, géré par le backend)
- Mode rejeu / historique des sessions passées (prévu en phase suivante)
- Refactoring des composants visuels existants
