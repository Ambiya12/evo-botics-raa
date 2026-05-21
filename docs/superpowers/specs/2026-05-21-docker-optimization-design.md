# Docker Optimization Design — Dev Environment

**Date :** 2026-05-21
**Branche cible :** `feature/Admin_dashboard`
**Scope :** Environnement de développement uniquement

---

## Contexte et problème

Le setup Docker actuel utilise l'image Laravel Sail stock (`ubuntu:24.04` + PHP 8.5 + Node.js 24 + tous les outils JS + toutes les extensions PHP). Cette image monolithique cause :

- **Taille excessive** : ~900–1 500 MB, incluant bun, pnpm, yarn, Playwright, clients PostgreSQL/MongoDB, extensions PHP inutilisées (mongodb, imap, ldap, swoole, imagick…)
- **Démarrage lent** : le conteneur PHP embarque Vite, donc un restart PHP coupe le HMR
- **I/O lent sur macOS** : `vendor/` et `node_modules/` montés depuis le host via bind-mount

## Approche retenue : Hybride Sail + Dockerfile custom + service Vite séparé

Garder `./vendor/bin/sail` et toutes ses commandes ergonomiques (`sail artisan`, `sail composer`, `sail npm`…), mais :

1. Remplacer l'image Sail par un `Dockerfile` custom local pointé depuis `compose.yaml`
2. Séparer Vite dans son propre service `node:24-alpine`
3. Isoler `vendor/` et `node_modules/` dans des volumes nommés Docker (élimine la lenteur I/O macOS)
4. Ajouter un `.dockerignore` pour réduire le build context

**Gain estimé :** ~900 MB → ~280 MB total, démarrage ×3 plus rapide, HMR isolé et stable.

---

## Architecture

```
compose.yaml
├── laravel.test   ← php:8.5-cli-bookworm custom   port ${APP_PORT:-80}
├── vite           ← node:24-alpine                 port ${VITE_PORT:-5173}
└── mysql          ← mysql:8.4 (inchangé)
```

### Fichiers créés / modifiés

```
reservationApp/
├── .docker/
│   └── php/
│       ├── Dockerfile        ← image PHP slim sur mesure
│       ├── start-container   ← copié de Sail, adapté
│       ├── supervisord.conf  ← copié de Sail
│       └── php.ini           ← copié de Sail
├── .dockerignore             ← nouveau
├── compose.yaml              ← mis à jour
├── vite.config.js            ← ajout server.host / hmr.host
├── README.md                 ← section Docker mise à jour
├── reservationApp/CLAUDE.md  ← section Commandes mise à jour
└── CLAUDE.md (racine)        ← structure mise à jour
```

---

## Détail des composants

### 1. Dockerfile PHP (`.docker/php/Dockerfile`)

- **Base :** `php:8.5-cli-bookworm` (image officielle PHP Debian slim)
- **Extensions installées :** `pdo_mysql`, `mbstring`, `xml`, `zip`, `bcmath`, `intl`, `curl`, `gd`, `pcov`
- **Supprimées vs Sail :** mongodb, imap, ldap, swoole, memcached, imagick, redis, pgsql, xdebug, Node.js
- **Conservé de Sail :** user `sail` (uid 1337, gid `WWWGROUP`), `start-container`, `supervisord.conf`, `php.ini`
- **Xdebug :** désactivé par défaut, peut être réactivé via `ARG INSTALL_XDEBUG=false` si besoin

### 2. `compose.yaml` — service `laravel.test`

```yaml
laravel.test:
    build:
        context: '.docker/php'
        dockerfile: Dockerfile
        args:
            WWWGROUP: '${WWWGROUP}'
    image: 'sail-8.5-custom/app'
    extra_hosts:
        - 'host.docker.internal:host-gateway'
    ports:
        - '${APP_PORT:-80}:80'
    environment:
        WWWUSER: '${WWWUSER}'
        LARAVEL_SAIL: 1
        XDEBUG_MODE: 'off'
    volumes:
        - '.:/var/www/html'
        - 'sail-vendor:/var/www/html/vendor'
    networks:
        - sail
    depends_on:
        - mysql
```

### 3. `compose.yaml` — service `vite` (nouveau)

```yaml
vite:
    image: 'node:24-alpine'
    working_dir: '/var/www/html'
    ports:
        - '${VITE_PORT:-5173}:5173'
    volumes:
        - '.:/var/www/html'
        - 'sail-node-modules:/var/www/html/node_modules'
    command: 'npm run dev -- --host'
    networks:
        - sail
```

- `--host` expose le serveur Vite sur `0.0.0.0` dans le conteneur
- Le volume nommé `sail-node-modules` évite le bind-mount macOS sur `node_modules/`

### 4. `vite.config.js` — config serveur HMR

```js
server: {
    host: '0.0.0.0',
    port: 5173,
    hmr: {
        host: 'localhost',
    },
},
```

- `host: '0.0.0.0'` : Vite écoute sur toutes les interfaces du conteneur
- `hmr.host: 'localhost'` : le navigateur se connecte au HMR via le port mappé par Docker

### 5. `.dockerignore`

```dockerignore
vendor/
node_modules/
public/build/
.git/
storage/logs/
storage/framework/cache/
*.log
.env
```

Réduit le build context de ~300 MB à quelques KB — rebuild quasi-instantané.

---

## Volumes nommés

| Volume | Contenu | Raison |
|---|---|---|
| `sail-vendor` | `vendor/` PHP | Évite I/O lent sur macOS, persist entre restarts |
| `sail-node-modules` | `node_modules/` JS | Idem |
| `sail-mysql` | Données MySQL | Inchangé (déjà en volume nommé) |

**Attention :** après le premier `sail up`, lancer `sail composer install` et `sail npm install` pour peupler les volumes.

---

## Commandes de développement après optimisation

```bash
# Démarrer tous les services
./vendor/bin/sail up -d

# Premier setup (peupler les volumes)
./vendor/bin/sail composer install
./vendor/bin/sail npm install

# Accès
# Laravel  → http://localhost:80
# Vite HMR → http://localhost:5173 (automatique via Inertia)

# Commandes courantes
./vendor/bin/sail artisan migrate
./vendor/bin/sail npm run build
./vendor/bin/sail composer require <package>

# Rebuild de l'image PHP après modification du Dockerfile
./vendor/bin/sail build --no-cache
```

---

## Contraintes et décisions

- **Pas de Nginx en dev** : `php artisan serve` via supervisord suffit pour le développement local
- **Pas de Redis** : les drivers `database` pour session/cache/queue restent inchangés — Redis pourra être ajouté plus tard sans toucher cette config
- **Sail conservé** : la commande `./vendor/bin/sail` wrape docker compose et reste l'interface principale
- **`vendor/` en volume nommé** : `sail composer install` doit être relancé après `sail build --no-cache` pour repeupler le volume. **Trade-off IDE** : le dossier `vendor/` sur le host restera vide — les extensions PHP (PHPStorm, VS Code Intelephense) ne verront plus les classes Composer. Si l'autocomplétion PHP est indispensable, `sail-vendor` peut être retiré du `compose.yaml` (laisser le bind-mount par défaut) au prix d'un I/O plus lent sur macOS.
- **`node_modules/` en volume nommé** : idem, le host ne verra pas `node_modules/`. Cela n'affecte pas les IDE TypeScript car VS Code résout les types via `tsconfig.json` et les `@types/*` déclarés — les types sont accessibles depuis le host via le bind-mount principal.
