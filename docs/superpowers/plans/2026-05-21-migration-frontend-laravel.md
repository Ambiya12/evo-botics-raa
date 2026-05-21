# Migration Frontend → Laravel/Inertia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Déplacer le dashboard admin React de `apps/frontend/` dans `reservationApp/` (Laravel/Inertia), servi via la route `/admin`, avec tests Vitest intégrés.

**Architecture:** Les fichiers source React sont copiés dans `resources/js/` en préservant leur structure relative — seuls `AdminDashboard.tsx` (déplacé de `src/app/` vers `Components/admin/`) et les pages internes (d'un niveau de profondeur supplémentaire) ont des imports à corriger. Une route Laravel `/admin` rend une page Inertia wrapper qui monte le composant `AdminDashboard` existant.

**Tech Stack:** React 18, Inertia.js (Laravel), Vite, Vitest, Dexie, Recharts, Lucide React, Laravel Echo / Pusher, Tailwind CSS + CSS plain

---

## Carte des fichiers

### Fichiers créés

| Source | Destination |
|---|---|
| *(nouveau)* | `reservationApp/vitest.config.ts` |
| `apps/frontend/src/test/setup.ts` | `reservationApp/resources/js/test/setup.ts` |
| `apps/frontend/src/types/admin.ts` | `reservationApp/resources/js/types/admin.ts` |
| `apps/frontend/src/types/__tests__/admin.test.ts` | `reservationApp/resources/js/types/__tests__/admin.test.ts` |
| `apps/frontend/src/constants/adminLabels.ts` | `reservationApp/resources/js/constants/adminLabels.ts` |
| `apps/frontend/src/data/mockAdminData.ts` | `reservationApp/resources/js/data/mockAdminData.ts` |
| `apps/frontend/src/services/**` | `reservationApp/resources/js/services/**` |
| `apps/frontend/src/hooks/**` | `reservationApp/resources/js/hooks/**` |
| `apps/frontend/src/components/ui/**` | `reservationApp/resources/js/Components/ui/**` |
| `apps/frontend/src/components/admin/**` | `reservationApp/resources/js/Components/admin/**` |
| `apps/frontend/src/pages/**` | `reservationApp/resources/js/Components/admin/pages/**` |
| `apps/frontend/src/app/AdminDashboard.tsx` | `reservationApp/resources/js/Components/admin/AdminDashboard.tsx` |
| `apps/frontend/src/styles.css` | `reservationApp/resources/css/admin.css` |
| *(nouveau)* | `reservationApp/resources/js/Pages/Admin/Dashboard.tsx` |

### Fichiers modifiés

| Fichier | Modification |
|---|---|
| `reservationApp/package.json` | Ajout deps : dexie, lucide-react, recharts, laravel-echo, pusher-js + devDeps vitest |
| `reservationApp/tsconfig.json` | Ajout `vitest.config.ts` dans `include` |
| `reservationApp/resources/css/app.css` | Ajout `@import './admin.css'` |
| `reservationApp/routes/web.php` | Ajout route `/admin` |
| `reservationApp/resources/js/Components/admin/AdminDashboard.tsx` | Correction des imports (10 lignes) |
| `reservationApp/resources/js/Components/admin/pages/*.tsx` | Correction des imports (sed) |
| `apps/CLAUDE.md` | Mise à jour : dashboard développé dans reservationApp |

### Fichiers supprimés

- `apps/frontend/` (entier, après validation)

---

## Task 1 : Dépendances et configuration Vitest

**Files:**
- Modify: `reservationApp/package.json`
- Modify: `reservationApp/tsconfig.json`
- Create: `reservationApp/vitest.config.ts`
- Create: `reservationApp/resources/js/test/setup.ts`

- [ ] **Étape 1 : Ajouter les dépendances dans package.json**

Dans `reservationApp/package.json`, ajouter dans `"devDependencies"` :

```json
"fake-indexeddb": "^6.2.5",
"jsdom": "^29.1.1",
"vitest": "^4.1.6",
"@vitest/coverage-v8": "^4.1.6",
"@testing-library/react": "^16.3.2",
"@testing-library/user-event": "^14.6.1"
```

Et ajouter dans `"devDependencies"` (ces packages sont des dépendances runtime dans apps/frontend mais des devDeps ici) :

```json
"dexie": "^4.4.2",
"dexie-react-hooks": "^4.4.0",
"lucide-react": "^0.468.0",
"recharts": "^3.8.1",
"laravel-echo": "^2.3.4",
"pusher-js": "^8.5.0"
```

Et ajouter dans `"scripts"` :

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Étape 2 : Créer vitest.config.ts**

Créer `reservationApp/vitest.config.ts` :

```typescript
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

- [ ] **Étape 3 : Ajouter vitest.config.ts au tsconfig**

Dans `reservationApp/tsconfig.json`, modifier `"include"` :

```json
"include": [
    "resources/js/**/*",
    "vite.config.ts",
    "vitest.config.ts"
]
```

- [ ] **Étape 4 : Créer le fichier de setup des tests**

Créer `reservationApp/resources/js/test/setup.ts` :

```typescript
// Global test environment setup — extend here as needed
```

- [ ] **Étape 5 : Installer les dépendances**

```bash
cd reservationApp && npm install
```

Résultat attendu : `added X packages` sans erreur.

- [ ] **Étape 6 : Vérifier que vitest se lance**

```bash
cd reservationApp && npm run test
```

Résultat attendu : `No test files found` (pas d'erreur de configuration).

- [ ] **Étape 7 : Commit**

```bash
git add reservationApp/package.json reservationApp/package-lock.json reservationApp/tsconfig.json reservationApp/vitest.config.ts reservationApp/resources/js/test/setup.ts
git commit -m "chore(reservationApp): add vitest and admin dashboard npm dependencies"
```

---

## Task 2 : Migration des types (avec test)

**Files:**
- Create: `reservationApp/resources/js/types/admin.ts`
- Create: `reservationApp/resources/js/types/__tests__/admin.test.ts`

- [ ] **Étape 1 : Copier le fichier de test en premier**

```bash
mkdir -p reservationApp/resources/js/types/__tests__
cp apps/frontend/src/types/__tests__/admin.test.ts reservationApp/resources/js/types/__tests__/admin.test.ts
```

- [ ] **Étape 2 : Lancer le test — vérifier qu'il échoue**

```bash
cd reservationApp && npm run test -- types
```

Résultat attendu : erreur `Cannot find module '../admin'`.

- [ ] **Étape 3 : Copier le fichier source**

```bash
mkdir -p reservationApp/resources/js/types
cp apps/frontend/src/types/admin.ts reservationApp/resources/js/types/admin.ts
```

- [ ] **Étape 4 : Lancer le test — vérifier qu'il passe**

```bash
cd reservationApp && npm run test -- types
```

Résultat attendu :
```
✓ resources/js/types/__tests__/admin.test.ts (1 test)
  ✓ ConnectionStatus > includes the 5 expected states
```

- [ ] **Étape 5 : Commit**

```bash
git add reservationApp/resources/js/types/
git commit -m "feat(admin): migrate admin TypeScript types into reservationApp"
```

---

## Task 3 : Migration des constantes et données mock

**Files:**
- Create: `reservationApp/resources/js/constants/adminLabels.ts`
- Create: `reservationApp/resources/js/data/mockAdminData.ts`

- [ ] **Étape 1 : Copier les fichiers**

```bash
mkdir -p reservationApp/resources/js/constants reservationApp/resources/js/data
cp apps/frontend/src/constants/adminLabels.ts reservationApp/resources/js/constants/adminLabels.ts
cp apps/frontend/src/data/mockAdminData.ts reservationApp/resources/js/data/mockAdminData.ts
```

- [ ] **Étape 2 : Vérifier que les tests existants passent toujours**

```bash
cd reservationApp && npm run test
```

Résultat attendu : toujours 1 test passé, 0 échoué.

- [ ] **Étape 3 : Commit**

```bash
git add reservationApp/resources/js/constants/ reservationApp/resources/js/data/
git commit -m "feat(admin): migrate admin constants and mock data into reservationApp"
```

---

## Task 4 : Migration des services (avec tests)

**Files:**
- Create: `reservationApp/resources/js/services/**`

- [ ] **Étape 1 : Copier les tests des services en premier**

```bash
mkdir -p reservationApp/resources/js/services/__tests__ reservationApp/resources/js/services/providers/__tests__
cp apps/frontend/src/services/__tests__/timeSeriesStore.test.ts \
   reservationApp/resources/js/services/__tests__/timeSeriesStore.test.ts
cp apps/frontend/src/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts \
   reservationApp/resources/js/services/providers/__tests__/laravelEchoRobotDataProvider.test.ts
```

- [ ] **Étape 2 : Lancer les tests — vérifier qu'ils échouent**

```bash
cd reservationApp && npm run test -- services
```

Résultat attendu : erreurs `Cannot find module`.

- [ ] **Étape 3 : Copier tous les fichiers de services**

```bash
mkdir -p reservationApp/resources/js/services/providers
cp apps/frontend/src/services/adminControlService.ts     reservationApp/resources/js/services/adminControlService.ts
cp apps/frontend/src/services/armJointService.ts          reservationApp/resources/js/services/armJointService.ts
cp apps/frontend/src/services/eventLogService.ts          reservationApp/resources/js/services/eventLogService.ts
cp apps/frontend/src/services/incidentService.ts          reservationApp/resources/js/services/incidentService.ts
cp apps/frontend/src/services/jetsonMetricsService.ts     reservationApp/resources/js/services/jetsonMetricsService.ts
cp apps/frontend/src/services/robotStatusService.ts       reservationApp/resources/js/services/robotStatusService.ts
cp apps/frontend/src/services/robotVideoService.ts        reservationApp/resources/js/services/robotVideoService.ts
cp apps/frontend/src/services/timeSeriesStore.ts          reservationApp/resources/js/services/timeSeriesStore.ts
cp apps/frontend/src/services/visitorSessionService.ts    reservationApp/resources/js/services/visitorSessionService.ts
cp apps/frontend/src/services/providers/armJointProvider.ts            reservationApp/resources/js/services/providers/armJointProvider.ts
cp apps/frontend/src/services/providers/connectionManagerStore.ts      reservationApp/resources/js/services/providers/connectionManagerStore.ts
cp apps/frontend/src/services/providers/jetsonMetricsProvider.ts       reservationApp/resources/js/services/providers/jetsonMetricsProvider.ts
cp apps/frontend/src/services/providers/laravelEchoEventLogProvider.ts reservationApp/resources/js/services/providers/laravelEchoEventLogProvider.ts
cp apps/frontend/src/services/providers/laravelEchoIncidentProvider.ts reservationApp/resources/js/services/providers/laravelEchoIncidentProvider.ts
cp apps/frontend/src/services/providers/laravelEchoRobotDataProvider.ts reservationApp/resources/js/services/providers/laravelEchoRobotDataProvider.ts
cp apps/frontend/src/services/providers/laravelEchoVisitorSessionProvider.ts reservationApp/resources/js/services/providers/laravelEchoVisitorSessionProvider.ts
cp apps/frontend/src/services/providers/mockArmJointProvider.ts        reservationApp/resources/js/services/providers/mockArmJointProvider.ts
cp apps/frontend/src/services/providers/mockJetsonMetricsProvider.ts   reservationApp/resources/js/services/providers/mockJetsonMetricsProvider.ts
cp apps/frontend/src/services/providers/mockRobotDataProvider.ts       reservationApp/resources/js/services/providers/mockRobotDataProvider.ts
cp apps/frontend/src/services/providers/robotStatusProvider.ts         reservationApp/resources/js/services/providers/robotStatusProvider.ts
cp apps/frontend/src/services/providers/websocketConnectionManager.ts  reservationApp/resources/js/services/providers/websocketConnectionManager.ts
```

- [ ] **Étape 4 : Lancer les tests — vérifier qu'ils passent**

```bash
cd reservationApp && npm run test -- services
```

Résultat attendu : tous les tests de services passés.

- [ ] **Étape 5 : Commit**

```bash
git add reservationApp/resources/js/services/
git commit -m "feat(admin): migrate admin services and providers into reservationApp"
```

---

## Task 5 : Migration des hooks (avec tests)

**Files:**
- Create: `reservationApp/resources/js/hooks/**`

- [ ] **Étape 1 : Copier le test du hook en premier**

```bash
mkdir -p reservationApp/resources/js/hooks/__tests__
cp apps/frontend/src/hooks/__tests__/useTimeSeriesData.test.ts \
   reservationApp/resources/js/hooks/__tests__/useTimeSeriesData.test.ts
```

- [ ] **Étape 2 : Lancer le test — vérifier qu'il échoue**

```bash
cd reservationApp && npm run test -- hooks
```

Résultat attendu : erreur `Cannot find module '../useTimeSeriesData'`.

- [ ] **Étape 3 : Copier les hooks**

```bash
mkdir -p reservationApp/resources/js/hooks
cp apps/frontend/src/hooks/useDashboardData.ts  reservationApp/resources/js/hooks/useDashboardData.ts
cp apps/frontend/src/hooks/useTimeSeriesData.ts reservationApp/resources/js/hooks/useTimeSeriesData.ts
```

- [ ] **Étape 4 : Lancer les tests — vérifier qu'ils passent**

```bash
cd reservationApp && npm run test -- hooks
```

Résultat attendu :
```
✓ resources/js/hooks/__tests__/useTimeSeriesData.test.ts (3 tests)
```

- [ ] **Étape 5 : Lancer tous les tests pour vérifier l'absence de régression**

```bash
cd reservationApp && npm run test
```

Résultat attendu : tous les tests passés.

- [ ] **Étape 6 : Commit**

```bash
git add reservationApp/resources/js/hooks/
git commit -m "feat(admin): migrate admin hooks into reservationApp"
```

---

## Task 6 : Migration des composants UI

**Files:**
- Create: `reservationApp/resources/js/Components/ui/`

- [ ] **Étape 1 : Copier les composants UI**

```bash
mkdir -p reservationApp/resources/js/Components/ui
cp apps/frontend/src/components/ui/MetricCard.tsx  reservationApp/resources/js/Components/ui/MetricCard.tsx
cp apps/frontend/src/components/ui/Panel.tsx        reservationApp/resources/js/Components/ui/Panel.tsx
cp apps/frontend/src/components/ui/Skeleton.tsx     reservationApp/resources/js/Components/ui/Skeleton.tsx
cp apps/frontend/src/components/ui/StatusBadge.tsx  reservationApp/resources/js/Components/ui/StatusBadge.tsx
```

- [ ] **Étape 2 : Vérifier que les tests passent toujours (pas de régression)**

```bash
cd reservationApp && npm run test
```

Résultat attendu : tous les tests passés.

- [ ] **Étape 3 : Commit**

```bash
git add reservationApp/resources/js/Components/ui/
git commit -m "feat(admin): migrate admin UI primitives (Panel, MetricCard, StatusBadge, Skeleton)"
```

---

## Task 7 : Migration des composants admin (panneaux)

**Files:**
- Create: `reservationApp/resources/js/Components/admin/` (panneaux uniquement — sans AdminDashboard)

Les composants dans `src/components/admin/` ont leurs imports relatifs préservés (même profondeur `../../types/`, `../../hooks/`, `../ui/`). Aucune correction d'import requise.

- [ ] **Étape 1 : Copier les composants admin**

```bash
mkdir -p reservationApp/resources/js/Components/admin
cp apps/frontend/src/components/admin/AdminShell.tsx                  reservationApp/resources/js/Components/admin/AdminShell.tsx
cp apps/frontend/src/components/admin/ArmStatusPanel.tsx              reservationApp/resources/js/Components/admin/ArmStatusPanel.tsx
cp apps/frontend/src/components/admin/CurrentVisitorSessionPanel.tsx  reservationApp/resources/js/Components/admin/CurrentVisitorSessionPanel.tsx
cp apps/frontend/src/components/admin/EventLogTable.tsx               reservationApp/resources/js/Components/admin/EventLogTable.tsx
cp apps/frontend/src/components/admin/IncidentMonitoringPanel.tsx     reservationApp/resources/js/Components/admin/IncidentMonitoringPanel.tsx
cp apps/frontend/src/components/admin/JetsonMetricsPanel.tsx          reservationApp/resources/js/Components/admin/JetsonMetricsPanel.tsx
cp apps/frontend/src/components/admin/RobotHealthPanel.tsx            reservationApp/resources/js/Components/admin/RobotHealthPanel.tsx
cp apps/frontend/src/components/admin/RobotStatusOverview.tsx         reservationApp/resources/js/Components/admin/RobotStatusOverview.tsx
cp apps/frontend/src/components/admin/SafetyActions.tsx               reservationApp/resources/js/Components/admin/SafetyActions.tsx
cp apps/frontend/src/components/admin/Sidebar.tsx                     reservationApp/resources/js/Components/admin/Sidebar.tsx
cp apps/frontend/src/components/admin/SlamMapPanel.tsx                reservationApp/resources/js/Components/admin/SlamMapPanel.tsx
cp apps/frontend/src/components/admin/TimeSeriesPanel.tsx             reservationApp/resources/js/Components/admin/TimeSeriesPanel.tsx
cp apps/frontend/src/components/admin/Topbar.tsx                      reservationApp/resources/js/Components/admin/Topbar.tsx
cp apps/frontend/src/components/admin/VideoFeedPanel.tsx              reservationApp/resources/js/Components/admin/VideoFeedPanel.tsx
```

- [ ] **Étape 2 : Vérifier que les tests passent toujours**

```bash
cd reservationApp && npm run test
```

Résultat attendu : tous les tests passés.

- [ ] **Étape 3 : Commit**

```bash
git add reservationApp/resources/js/Components/admin/
git commit -m "feat(admin): migrate admin panel components into reservationApp"
```

---

## Task 8 : Migration des pages internes (avec correction des imports)

**Files:**
- Create: `reservationApp/resources/js/Components/admin/pages/`

Les pages passent de `src/pages/` (depth 2) à `resources/js/Components/admin/pages/` (depth 4). Deux patterns d'import changent :
- `from "../components/admin/Xxx"` → `from "../Xxx"`
- `from "../types/admin"` → `from "../../../types/admin"`

- [ ] **Étape 1 : Copier les pages**

```bash
mkdir -p reservationApp/resources/js/Components/admin/pages
cp apps/frontend/src/pages/IncidentsPage.tsx  reservationApp/resources/js/Components/admin/pages/IncidentsPage.tsx
cp apps/frontend/src/pages/LiveStatusPage.tsx reservationApp/resources/js/Components/admin/pages/LiveStatusPage.tsx
cp apps/frontend/src/pages/MapPage.tsx        reservationApp/resources/js/Components/admin/pages/MapPage.tsx
cp apps/frontend/src/pages/OverviewPage.tsx   reservationApp/resources/js/Components/admin/pages/OverviewPage.tsx
cp apps/frontend/src/pages/SafetyPage.tsx     reservationApp/resources/js/Components/admin/pages/SafetyPage.tsx
cp apps/frontend/src/pages/SessionsPage.tsx   reservationApp/resources/js/Components/admin/pages/SessionsPage.tsx
cp apps/frontend/src/pages/SettingsPage.tsx   reservationApp/resources/js/Components/admin/pages/SettingsPage.tsx
```

- [ ] **Étape 2 : Corriger les imports — composants admin**

```bash
cd reservationApp
find resources/js/Components/admin/pages -name "*.tsx" \
  -exec sed -i '' 's|from "\.\./components/admin/|from "../|g' {} +
```

- [ ] **Étape 3 : Corriger les imports — types**

```bash
cd reservationApp
find resources/js/Components/admin/pages -name "*.tsx" \
  -exec sed -i '' 's|from "\.\./types/|from "../../../types/|g' {} +
```

- [ ] **Étape 4 : Corriger les imports — hooks**

```bash
cd reservationApp
find resources/js/Components/admin/pages -name "*.tsx" \
  -exec sed -i '' 's|from "\.\./hooks/|from "../../../hooks/|g' {} +
```

- [ ] **Étape 5 : Corriger les imports — services**

```bash
cd reservationApp
find resources/js/Components/admin/pages -name "*.tsx" \
  -exec sed -i '' 's|from "\.\./services/|from "../../../services/|g' {} +
```

- [ ] **Étape 6 : Vérifier les imports avec TypeScript**

```bash
cd reservationApp && npx tsc --noEmit 2>&1 | grep "Components/admin/pages" | head -20
```

Résultat attendu : aucune erreur dans `Components/admin/pages/`.

- [ ] **Étape 7 : Commit**

```bash
git add reservationApp/resources/js/Components/admin/pages/
git commit -m "feat(admin): migrate internal admin pages into reservationApp"
```

---

## Task 9 : Migration de AdminDashboard.tsx (correction des imports)

**Files:**
- Create: `reservationApp/resources/js/Components/admin/AdminDashboard.tsx`

`AdminDashboard.tsx` est déplacé de `src/app/` vers `Components/admin/` — les imports changent selon cette table :

| Import original | Import corrigé |
|---|---|
| `from "../components/admin/AdminShell"` | `from "./AdminShell"` |
| `from "../components/ui/Skeleton"` | `from "../ui/Skeleton"` |
| `from "../hooks/useDashboardData"` | `from "../../hooks/useDashboardData"` |
| `from "../pages/IncidentsPage"` | `from "./pages/IncidentsPage"` |
| `from "../pages/LiveStatusPage"` | `from "./pages/LiveStatusPage"` |
| `from "../pages/MapPage"` | `from "./pages/MapPage"` |
| `from "../pages/OverviewPage"` | `from "./pages/OverviewPage"` |
| `from "../pages/SafetyPage"` | `from "./pages/SafetyPage"` |
| `from "../pages/SessionsPage"` | `from "./pages/SessionsPage"` |
| `from "../pages/SettingsPage"` | `from "./pages/SettingsPage"` |
| `from "../types/admin"` | `from "../../types/admin"` |

- [ ] **Étape 1 : Copier AdminDashboard.tsx**

```bash
cp apps/frontend/src/app/AdminDashboard.tsx \
   reservationApp/resources/js/Components/admin/AdminDashboard.tsx
```

- [ ] **Étape 2 : Corriger les imports d'AdminShell et Skeleton**

```bash
cd reservationApp
sed -i '' \
  's|from "\.\./components/admin/AdminShell"|from "./AdminShell"|g' \
  resources/js/Components/admin/AdminDashboard.tsx
sed -i '' \
  's|from "\.\./components/ui/Skeleton"|from "../ui/Skeleton"|g' \
  resources/js/Components/admin/AdminDashboard.tsx
```

- [ ] **Étape 3 : Corriger les imports des hooks et types**

```bash
cd reservationApp
sed -i '' \
  's|from "\.\./hooks/useDashboardData"|from "../../hooks/useDashboardData"|g' \
  resources/js/Components/admin/AdminDashboard.tsx
sed -i '' \
  's|from "\.\./types/admin"|from "../../types/admin"|g' \
  resources/js/Components/admin/AdminDashboard.tsx
```

- [ ] **Étape 4 : Corriger les imports des pages**

```bash
cd reservationApp
sed -i '' 's|from "\.\./pages/|from "./pages/|g' \
  resources/js/Components/admin/AdminDashboard.tsx
```

- [ ] **Étape 5 : Vérifier les imports avec TypeScript**

```bash
cd reservationApp && npx tsc --noEmit 2>&1 | grep "AdminDashboard" | head -20
```

Résultat attendu : aucune erreur sur `AdminDashboard.tsx`.

- [ ] **Étape 6 : Vérifier la totalité des erreurs TypeScript**

```bash
cd reservationApp && npx tsc --noEmit 2>&1 | head -40
```

Résultat attendu : 0 erreur (ou uniquement des erreurs préexistantes non liées à la migration).

- [ ] **Étape 7 : Commit**

```bash
git add reservationApp/resources/js/Components/admin/AdminDashboard.tsx
git commit -m "feat(admin): migrate AdminDashboard component with corrected import paths"
```

---

## Task 10 : Page Inertia wrapper + Route Laravel

**Files:**
- Create: `reservationApp/resources/js/Pages/Admin/Dashboard.tsx`
- Modify: `reservationApp/routes/web.php`

- [ ] **Étape 1 : Créer la page Inertia**

Créer `reservationApp/resources/js/Pages/Admin/Dashboard.tsx` :

```tsx
import { AdminDashboard } from '../../Components/admin/AdminDashboard';

export default function AdminDashboardPage() {
    return <AdminDashboard />;
}
```

- [ ] **Étape 2 : Ajouter la route dans web.php**

Dans `reservationApp/routes/web.php`, ajouter avant la ligne `require __DIR__.'/auth.php';` :

```php
Route::get('/admin', fn () => Inertia::render('Admin/Dashboard'))->name('admin.dashboard');
```

- [ ] **Étape 3 : Vérifier les routes enregistrées**

```bash
cd reservationApp && php artisan route:list | grep admin
```

Résultat attendu :
```
GET|HEAD  admin  admin.dashboard  Closure
```

- [ ] **Étape 4 : Commit**

```bash
git add reservationApp/resources/js/Pages/Admin/ reservationApp/routes/web.php
git commit -m "feat(admin): add Inertia page wrapper and /admin Laravel route"
```

---

## Task 11 : Migration du CSS

**Files:**
- Create: `reservationApp/resources/css/admin.css`
- Modify: `reservationApp/resources/css/app.css`

- [ ] **Étape 1 : Copier le CSS**

```bash
cp apps/frontend/src/styles.css reservationApp/resources/css/admin.css
```

- [ ] **Étape 2 : Importer admin.css dans app.css**

Dans `reservationApp/resources/css/app.css`, ajouter à la fin du fichier :

```css
@import './admin.css';
```

- [ ] **Étape 3 : Commit**

```bash
git add reservationApp/resources/css/admin.css reservationApp/resources/css/app.css
git commit -m "feat(admin): add admin dashboard CSS to Laravel asset pipeline"
```

---

## Task 12 : Vérification finale — build et tests

- [ ] **Étape 1 : Lancer tous les tests**

```bash
cd reservationApp && npm run test
```

Résultat attendu : tous les tests passés (types, services, hooks).

- [ ] **Étape 2 : Lancer le build de production**

```bash
cd reservationApp && npm run build
```

Résultat attendu : build sans erreur, fichiers dans `public/build/`.

- [ ] **Étape 3 : Démarrer le serveur de développement**

```bash
cd reservationApp && php artisan serve &
npm run dev
```

- [ ] **Étape 4 : Ouvrir `/admin` dans le navigateur**

Ouvrir `http://localhost:8000/admin`.

Résultat attendu : le dashboard admin s'affiche avec la navigation (Overview, Live Status, Sessions, Incidents, Map, Safety, Settings) et les métriques mock.

- [ ] **Étape 5 : Vérifier la navigation interne**

Cliquer sur chaque page du menu. Résultat attendu : chaque page se charge sans erreur console.

---

## Task 13 : Nettoyage et documentation

**Files:**
- Modify: `apps/CLAUDE.md`
- Delete: `apps/frontend/`

- [ ] **Étape 1 : Mettre à jour apps/CLAUDE.md**

Dans `apps/CLAUDE.md`, remplacer la section "Structure" par :

```markdown
## Structure

```
apps/
├── frontend/   ← ARCHIVÉ — le dashboard admin est désormais dans reservationApp/resources/js/
└── backend/    ← API Node.js réservations + notifications (non démarré)
```

Le dashboard admin React est servi par Laravel/Inertia à `/admin`.
Source : `reservationApp/resources/js/Components/admin/`
Pour brancher le vrai robot : `setRobotStatusProvider()` dans `reservationApp/resources/js/services/robotStatusService.ts`
```

- [ ] **Étape 2 : Supprimer apps/frontend/**

```bash
rm -rf apps/frontend/
```

- [ ] **Étape 3 : Commit final**

```bash
git add apps/CLAUDE.md
git rm -r apps/frontend/
git commit -m "feat(admin): complete migration of dashboard into Laravel/Inertia — remove apps/frontend"
```
