# Design : Migration du dashboard admin dans Laravel/Inertia

**Date** : 2026-05-21  
**Branche** : `feature/Admin_dashboard`  
**Décision** : Option A — migration complète dans Laravel/Inertia.js

---

## Contexte

Le dashboard admin opérateur (`apps/frontend/`) est une SPA React 18 + Vite standalone qui monitore le robot en temps réel (WebSocket rosbridge, métriques Jetson, bras, SLAM, vidéo). Il a été développé séparément de l'app Laravel (`reservationApp/`) qui gère les réservations de salles via QR code.

**Contrainte** : déploiement simplifié — tout doit être servi depuis un seul serveur Laravel.

**Observation clé** : `reservationApp/` utilise déjà Inertia.js + React 18 + Vite. La migration est naturelle. Le dashboard n'utilise pas React Router (navigation `activePage` par `useState`), donc aucun refactoring de routing n'est nécessaire.

---

## Architecture cible

```
reservationApp/resources/js/
├── Pages/
│   ├── Admin/
│   │   └── Dashboard.tsx          ← Page Inertia (wrapper fin)
│   ├── Dashboard.tsx              ← Existant (inchangé)
│   └── Auth/ ...                  ← Existant (inchangé)
├── Components/
│   ├── admin/                     ← Migré depuis apps/frontend/src/components/admin/ + src/app/
│   │   ├── AdminDashboard.tsx     ← Déplacé depuis src/app/AdminDashboard.tsx
│   │   ├── AdminShell.tsx
│   │   ├── ArmStatusPanel.tsx
│   │   ├── CurrentVisitorSessionPanel.tsx
│   │   ├── EventLogTable.tsx
│   │   ├── JetsonMetricsPanel.tsx
│   │   ├── RobotHealthPanel.tsx
│   │   ├── RobotStatusOverview.tsx
│   │   ├── SafetyActions.tsx
│   │   ├── SlamMapPanel.tsx
│   │   ├── Topbar.tsx
│   │   └── VideoFeedPanel.tsx
│   └── ui/                        ← Migré depuis apps/frontend/src/components/ui/
│       ├── MetricCard.tsx
│       ├── Panel.tsx
│       ├── Skeleton.tsx
│       └── StatusBadge.tsx
├── hooks/                         ← Migré depuis apps/frontend/src/hooks/
│   ├── useDashboardData.ts
│   └── useTimeSeriesData.ts
├── services/                      ← Migré depuis apps/frontend/src/services/
│   ├── providers/
│   │   ├── robotStatusProvider.ts
│   │   └── mockRobotDataProvider.ts
│   ├── adminControlService.ts
│   ├── armJointService.ts
│   ├── eventLogService.ts
│   ├── incidentService.ts
│   ├── jetsonMetricsService.ts
│   ├── robotStatusService.ts
│   ├── robotVideoService.ts
│   ├── timeSeriesStore.ts
│   └── visitorSessionService.ts
├── types/                         ← Migré depuis apps/frontend/src/types/
│   ├── admin.ts
│   └── __tests__/
│       └── admin.test.ts
├── constants/                     ← Migré depuis apps/frontend/src/constants/
│   └── adminLabels.ts
└── data/                          ← Migré depuis apps/frontend/src/data/
    └── mockAdminData.ts
```

---

## Routing Laravel

Ajout dans `routes/web.php` :

```php
Route::get('/admin', fn() => Inertia::render('Admin/Dashboard'))
    ->name('admin.dashboard');
```

Pas de middleware `auth` pour l'instant (le dashboard robot a une auth séparée, non définie).

Page Inertia `resources/js/Pages/Admin/Dashboard.tsx` :

```tsx
import { AdminDashboard } from '../../Components/admin/AdminDashboard';

export default function AdminDashboardPage() {
    return <AdminDashboard />;
}
```

La navigation interne (`activePage` useState, switch de pages) reste **identique** — Inertia est transparent pour le dashboard.

---

## CSS

`apps/frontend/src/styles.css` est copié vers `resources/css/admin.css`.

Ajout dans `resources/css/app.css` :

```css
@import './admin.css';
```

Pas de conflit avec Tailwind — les deux coexistent dans le même build Vite.

---

## Dépendances à ajouter dans `reservationApp/package.json`

### dependencies
| Paquet | Version | Rôle |
|---|---|---|
| `dexie` | `^4.4.2` | IndexedDB (timeSeriesStore) |
| `dexie-react-hooks` | `^4.4.0` | Hooks Dexie |
| `lucide-react` | `^0.468.0` | Icônes |
| `recharts` | `^3.8.1` | Graphiques |
| `laravel-echo` | `^2.3.4` | WebSocket (futur rosbridge) |
| `pusher-js` | `^8.5.0` | Transport WebSocket |

### devDependencies
| Paquet | Version | Rôle |
|---|---|---|
| `vitest` | `^4.1.6` | Runner de tests |
| `@vitest/coverage-v8` | `^4.1.6` | Coverage |
| `@testing-library/react` | `^16.3.2` | Tests composants |
| `@testing-library/user-event` | `^14.6.1` | Simulation interactions |
| `jsdom` | `^29.1.1` | DOM virtuel |
| `fake-indexeddb` | `^6.2.5` | Mock IndexedDB pour Dexie |

---

## Tests

Ajout de scripts dans `reservationApp/package.json` :
```json
"test": "vitest run",
"test:watch": "vitest"
```

Création de `reservationApp/vitest.config.ts` :
```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    test: {
        environment: 'jsdom',
        setupFiles: ['./resources/js/test/setup.ts'],
    },
});
```

Fichiers de test migrés :
- `apps/frontend/src/test/setup.ts` → `resources/js/test/setup.ts`
- `apps/frontend/src/types/__tests__/admin.test.ts` → `resources/js/types/__tests__/admin.test.ts`

---

## Sort de `apps/frontend/`

Une fois la migration validée (build OK, `/admin` accessible, tests verts) :
- Supprimer `apps/frontend/`
- Mettre à jour `apps/CLAUDE.md` : le dashboard se développe désormais dans `reservationApp/resources/js/`
- Le `apps/backend/` reste inchangé (non démarré)

---

## Ce qui ne change pas

- Toute la logique React (hooks, services, composants, types)
- Le provider pattern pour le swap rosbridge (`setRobotStatusProvider()`)
- La navigation interne single-view du dashboard
- Les règles MVP : arrêt d'urgence ≤ 1 seconde
- L'app de réservation Laravel (routes, controllers, modèles)
