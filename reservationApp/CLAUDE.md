# CLAUDE.md — reservationApp/

## Mission

Application Laravel 12 + React 18 (Inertia.js + Vite) gérant les réservations QR code et le dashboard opérateur du robot.

## Structure

```
reservationApp/
├── app/                        ← Controllers, Models Laravel
├── routes/web.php              ← Routes : / (Welcome), /admin (dashboard), /dashboard (auth)
├── resources/
│   ├── css/app.css             ← Entrée CSS : @import avant @tailwind (ordre obligatoire)
│   └── js/
│       ├── app.tsx             ← Point d'entrée Inertia
│       ├── Pages/Admin/        ← Page Inertia pour /admin → Admin/Dashboard
│       ├── Components/admin/   ← Composants dashboard (panels, topbar, shell)
│       │   └── pages/          ← Sous-pages SPA : Overview, LiveStatus, Sessions…
│       ├── Components/ui/      ← Composants génériques (Panel, MetricCard, StatusBadge…)
│       ├── hooks/              ← useDashboardData, useTimeSeriesData
│       ├── services/           ← Services métier (robotStatus, incident, eventLog…)
│       │   └── providers/      ← Implémentations mock/* et laravelEcho/*
│       ├── types/admin.ts      ← Types TypeScript centralisés
│       ├── data/mockAdminData.ts
│       └── constants/adminLabels.ts
└── public/build/               ← Généré par Vite (gitignored, ne pas éditer)
```

## Commandes

```bash
# Développement avec Docker/Sail (méthode principale)
./vendor/bin/sail up -d

# Premier démarrage — peupler les volumes (une seule fois, ou après sail build --no-cache)
./vendor/bin/sail composer install
docker compose exec vite npm install

# Laravel  → http://localhost
# Vite HMR → http://localhost:5173 (lancé automatiquement par le service vite)

# Commandes Artisan
./vendor/bin/sail artisan migrate
./vendor/bin/sail artisan tinker

# Commandes npm — via le service vite (node absent du conteneur PHP)
docker compose exec vite npm run build
docker compose exec vite npm install <package>

# Rebuild de l'image PHP (après modification de .docker/php/Dockerfile)
./vendor/bin/sail build --no-cache && ./vendor/bin/sail up -d
./vendor/bin/sail composer install   # repeupler le volume vendor/

# Tests
./vendor/bin/sail artisan test       # PHPUnit (Laravel)
npm test                             # vitest local (sans Docker, nécessite node local)
```

## Conventions

- Alias d'import : `@/*` → `resources/js/*` (configuré dans tsconfig.json et vite.config.js).
- TypeScript strict activé — pas de `any` implicite.
- Pattern provider : chaque service expose `setXxxProvider()` pour swapper mock ↔ rosbridge sans toucher aux composants.
- Les providers mock sont actifs par défaut ; les providers `laravelEcho*` sont pour le vrai robot.
- Tests dans `__tests__/` à côté du fichier testé, ou dans `types/__tests__/`.

## Règles importantes

- IMPORTANT : `@import` doit toujours précéder `@tailwind` dans les fichiers CSS — PostCSS plante sinon.
- IMPORTANT : La route `/admin` n'a pas de middleware `auth` — accessible sans connexion (mode opérateur).
- NE JAMAIS éditer les fichiers dans `public/build/` — ils sont générés par Vite.
- TOUJOURS swapper le provider via `setRobotStatusProvider()` (et équivalents) pour brancher le vrai robot, ne pas modifier le service directement.
- Les tests utilisent `jsdom` + `fake-indexeddb` — ne pas introduire de dépendances navigateur natives sans adapter le setup.
