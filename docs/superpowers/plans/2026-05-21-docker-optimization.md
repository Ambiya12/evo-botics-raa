# Docker Dev Environment Optimization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remplacer l'image Laravel Sail monolithique par un Dockerfile PHP slim custom + un service Vite séparé, réduisant la taille totale de ~900 MB à ~280 MB et le temps de démarrage d'un facteur 3.

**Architecture:** Service `laravel.test` basé sur `php:8.5-cli-bookworm` avec uniquement les extensions PHP du projet. Service `vite` basé sur `node:24-alpine`, indépendant. Volumes nommés pour `vendor/` et `node_modules/` pour éliminer la lenteur I/O macOS.

**Tech Stack:** Docker, php:8.5-cli-bookworm, node:24-alpine, Laravel Sail CLI, supervisord, Composer, Vite 7

---

## Carte des fichiers

| Fichier | Action | Rôle |
|---|---|---|
| `reservationApp/.docker/php/Dockerfile` | Créer | Image PHP slim custom |
| `reservationApp/.docker/php/start-container` | Créer (copie Sail) | Entrypoint du conteneur PHP |
| `reservationApp/.docker/php/supervisord.conf` | Créer (copie Sail) | Lance php artisan serve |
| `reservationApp/.docker/php/php.ini` | Créer (copie Sail) | Config PHP (upload, pcov) |
| `reservationApp/.dockerignore` | Créer | Réduit le build context |
| `reservationApp/compose.yaml` | Modifier | Ajoute service vite, volumes nommés, new build context |
| `reservationApp/vite.config.js` | Modifier | HMR cross-container (host 0.0.0.0) |
| `README.md` | Modifier | Section Docker dev mise à jour |
| `reservationApp/CLAUDE.md` | Modifier | Commandes npm via service vite |

---

## Task 1 : Créer `.docker/php/` et copier les fichiers support Sail

**Files:**
- Create: `reservationApp/.docker/php/start-container`
- Create: `reservationApp/.docker/php/supervisord.conf`
- Create: `reservationApp/.docker/php/php.ini`

Ces fichiers sont copiés tels quels depuis `vendor/laravel/sail/runtimes/8.5/` — ils sont déjà corrects pour notre usage.

- [ ] **Step 1 : Créer le dossier**

```bash
mkdir -p reservationApp/.docker/php
```

- [ ] **Step 2 : Copier `start-container`**

Créer `reservationApp/.docker/php/start-container` avec ce contenu exact :

```bash
#!/usr/bin/env bash

if [ "$SUPERVISOR_PHP_USER" != "root" ] && [ "$SUPERVISOR_PHP_USER" != "sail" ]; then
    echo "You should set SUPERVISOR_PHP_USER to either 'sail' or 'root'."
    exit 1
fi

if [ ! -z "$WWWUSER" ]; then
    usermod -u $WWWUSER sail
fi

if [ ! -d /.composer ]; then
    mkdir /.composer
fi

chmod -R ugo+rw /.composer

if [ $# -gt 0 ]; then
    if [ "$SUPERVISOR_PHP_USER" = "root" ]; then
        exec "$@"
    else
        exec gosu $WWWUSER "$@"
    fi
else
    exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
fi
```

- [ ] **Step 3 : Copier `supervisord.conf`**

Créer `reservationApp/.docker/php/supervisord.conf` avec ce contenu exact :

```ini
[supervisord]
nodaemon=true
user=root
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid

[program:php]
command=%(ENV_SUPERVISOR_PHP_COMMAND)s
user=%(ENV_SUPERVISOR_PHP_USER)s
environment=LARAVEL_SAIL="1"
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

- [ ] **Step 4 : Copier `php.ini`**

Créer `reservationApp/.docker/php/php.ini` avec ce contenu exact :

```ini
[PHP]
post_max_size = 100M
upload_max_filesize = 100M
variables_order = EGPCS
pcov.directory = .
```

- [ ] **Step 5 : Commit**

```bash
git add reservationApp/.docker/
git commit -m "chore(docker): add php support files from sail runtime"
```

---

## Task 2 : Écrire le Dockerfile PHP custom

**Files:**
- Create: `reservationApp/.docker/php/Dockerfile`

Base `php:8.5-cli-bookworm` (image officielle Debian slim). Seules les extensions réellement utilisées par ce projet sont installées. Node.js est absent — Vite tourne dans son propre service.

Différences clés vs image Sail :
- Pas de Node.js, bun, pnpm, yarn, Playwright
- Pas de php-pgsql, php-mongodb, php-imap, php-ldap, php-swoole, php-memcached, php-imagick, php-xdebug
- Path PHP : `/usr/local/bin/php` (officiel Docker) vs `/usr/bin/php8.5` (ubuntu/ondrej)
- Config PHP dans `/usr/local/etc/php/conf.d/` (officiel Docker)

- [ ] **Step 1 : Créer `reservationApp/.docker/php/Dockerfile`**

```dockerfile
FROM php:8.5-cli-bookworm

LABEL maintainer="reservationApp"

ARG WWWGROUP

WORKDIR /var/www/html

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC
ENV LANG=C.UTF-8
ENV SUPERVISOR_PHP_COMMAND="/usr/local/bin/php -d variables_order=EGPCS /var/www/html/artisan serve --host=0.0.0.0 --port=80"
ENV SUPERVISOR_PHP_USER="sail"

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
        gosu \
        curl \
        ca-certificates \
        zip \
        unzip \
        git \
        supervisor \
        libcap2-bin \
        libpng-dev \
        libfreetype6-dev \
        libjpeg62-turbo-dev \
        libxml2-dev \
        libzip-dev \
        libicu-dev \
    && docker-php-ext-configure gd --with-freetype --with-jpeg \
    && docker-php-ext-install -j$(nproc) \
        pdo_mysql \
        mbstring \
        xml \
        zip \
        bcmath \
        intl \
        gd \
    && pecl install pcov \
    && docker-php-ext-enable pcov \
    && curl -sLS https://getcomposer.org/installer | php -- --install-dir=/usr/bin/ --filename=composer \
    && apt-get -y autoremove \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

RUN setcap "cap_net_bind_service=+ep" /usr/local/bin/php

RUN groupadd --force -g $WWWGROUP sail \
    && useradd -ms /bin/bash --no-user-group -g $WWWGROUP -u 1337 sail \
    && git config --global --add safe.directory /var/www/html

COPY start-container /usr/local/bin/start-container
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY php.ini /usr/local/etc/php/conf.d/99-sail.ini
RUN chmod +x /usr/local/bin/start-container

EXPOSE 80/tcp

ENTRYPOINT ["start-container"]
```

- [ ] **Step 2 : Vérifier le contexte de build (les 4 fichiers sont bien présents)**

```bash
ls reservationApp/.docker/php/
```

Attendu : `Dockerfile  php.ini  start-container  supervisord.conf`

- [ ] **Step 3 : Commit**

```bash
git add reservationApp/.docker/php/Dockerfile
git commit -m "chore(docker): add custom slim php 8.5 dockerfile"
```

---

## Task 3 : Créer `.dockerignore`

**Files:**
- Create: `reservationApp/.dockerignore`

Sans ce fichier, Docker transfère ~300 MB de `vendor/` et `node_modules/` au daemon à chaque build. Avec lui, le build context tombe à quelques Ko.

- [ ] **Step 1 : Créer `reservationApp/.dockerignore`**

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

- [ ] **Step 2 : Commit**

```bash
git add reservationApp/.dockerignore
git commit -m "chore(docker): add .dockerignore to reduce build context"
```

---

## Task 4 : Mettre à jour `compose.yaml`

**Files:**
- Modify: `reservationApp/compose.yaml`

Changements :
- `laravel.test` : build context pointé vers `.docker/php`, volume nommé `sail-vendor`, port Vite retiré
- Ajout du service `vite` (`node:24-alpine`, port 5173, volume nommé `sail-node-modules`)
- Ajout des volumes nommés `sail-vendor` et `sail-node-modules`

- [ ] **Step 1 : Remplacer le contenu de `reservationApp/compose.yaml`**

```yaml
services:
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
            IGNITION_LOCAL_SITES_PATH: '${PWD}'
        volumes:
            - '.:/var/www/html'
            - 'sail-vendor:/var/www/html/vendor'
        networks:
            - sail
        depends_on:
            - mysql
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
    mysql:
        image: 'mysql:8.4'
        ports:
            - '${FORWARD_DB_PORT:-3306}:3306'
        environment:
            MYSQL_ROOT_PASSWORD: '${DB_PASSWORD}'
            MYSQL_ROOT_HOST: '%'
            MYSQL_DATABASE: '${DB_DATABASE}'
            MYSQL_USER: '${DB_USERNAME}'
            MYSQL_PASSWORD: '${DB_PASSWORD}'
            MYSQL_ALLOW_EMPTY_PASSWORD: 1
            MYSQL_EXTRA_OPTIONS: '${MYSQL_EXTRA_OPTIONS:-}'
        volumes:
            - 'sail-mysql:/var/lib/mysql'
            - './vendor/laravel/sail/database/mysql/create-testing-database.sh:/docker-entrypoint-initdb.d/10-create-testing-database.sh'
        networks:
            - sail
        healthcheck:
            test:
                - CMD
                - mysqladmin
                - ping
                - '-p${DB_PASSWORD}'
            retries: 3
            timeout: 5s
networks:
    sail:
        driver: bridge
volumes:
    sail-mysql:
        driver: local
    sail-vendor:
        driver: local
    sail-node-modules:
        driver: local
```

> **Note MySQL :** Le bind-mount du script d'init (`./vendor/laravel/sail/database/...`) utilise le `vendor/` du **host** (pas du conteneur PHP). Ce dossier existe toujours sur le host — le bind-mount fonctionne normalement.

- [ ] **Step 2 : Commit**

```bash
git add reservationApp/compose.yaml
git commit -m "chore(docker): split vite service, use slim php image and named volumes"
```

---

## Task 5 : Mettre à jour `vite.config.js`

**Files:**
- Modify: `reservationApp/vite.config.js`

Sans cette config, le serveur Vite écoute sur `127.0.0.1` à l'intérieur du conteneur — injoignable depuis le host. `host: '0.0.0.0'` expose Vite sur toutes les interfaces du conteneur. `hmr.host: 'localhost'` dit au navigateur de se connecter au HMR via le port mappé par Docker.

- [ ] **Step 1 : Remplacer le contenu de `reservationApp/vite.config.js`**

```js
import { defineConfig } from 'vite';
import laravel from 'laravel-vite-plugin';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [
        laravel({
            input: 'resources/js/app.tsx',
            refresh: true,
        }),
        react(),
    ],
    server: {
        host: '0.0.0.0',
        port: 5173,
        hmr: {
            host: 'localhost',
        },
    },
});
```

- [ ] **Step 2 : Commit**

```bash
git add reservationApp/vite.config.js
git commit -m "chore(vite): expose dev server and HMR for docker container"
```

---

## Task 6 : Build et vérification du setup

Cette tâche valide que toute la chaîne fonctionne. Pas de tests unitaires possibles pour de l'infra Docker — on vérifie par smoke tests.

Travailler depuis `reservationApp/` pour les commandes sail/docker.

- [ ] **Step 1 : Supprimer l'ancienne image Sail si elle existe**

```bash
cd reservationApp
docker image rm sail-8.5/app 2>/dev/null || true
```

- [ ] **Step 2 : Builder la nouvelle image PHP**

```bash
./vendor/bin/sail build --no-cache
```

Attendu : build sans erreur, dernière ligne `=> exporting to image`. Si une extension échoue, vérifier que la lib apt correspondante est bien dans le `apt-get install` du Dockerfile (ex. `libzip-dev` pour `zip`).

- [ ] **Step 3 : Peupler node_modules/ AVANT de démarrer les services**

> Si `node_modules/` est vide quand le service `vite` démarre, `npm run dev` échoue immédiatement et le conteneur crashe. Il faut donc installer les packages dans le volume avant le premier `up`.
>
> `sail npm` ne fonctionne plus (node absent du conteneur PHP) — utiliser `docker compose run`.

```bash
docker compose run --rm vite npm install
```

Attendu : `added NNN packages` sans erreur. Cette commande crée un conteneur one-off qui peuple le volume `sail-node-modules`, puis s'arrête.

- [ ] **Step 4 : Démarrer tous les services**

```bash
./vendor/bin/sail up -d
```

Attendu : `[+] Running 3/3` (laravel.test, vite, mysql). Si un service n'est pas `healthy`, inspecter ses logs :

```bash
docker compose logs laravel.test
docker compose logs vite
```

- [ ] **Step 5 : Peupler le volume vendor/ (premier démarrage)**

```bash
./vendor/bin/sail composer install
```

Attendu : Composer résout les dépendances dans le volume `sail-vendor` à l'intérieur du conteneur.

- [ ] **Step 6 : Smoke test Laravel**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost
```

Attendu : `200` (ou `302` si la route `/` redirige).

- [ ] **Step 7 : Smoke test Vite**

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:5173
```

Attendu : `200`.

- [ ] **Step 8 : Vérifier le HMR dans le navigateur**

1. Ouvrir `http://localhost` dans le navigateur
2. Ouvrir `reservationApp/resources/js/Pages/Admin/Dashboard.tsx` (ou n'importe quel composant React)
3. Modifier une chaîne visible et sauvegarder
4. Vérifier que la page se met à jour sans rechargement complet

- [ ] **Step 9 : Vérifier la taille des images**

```bash
docker images | grep -E 'sail|node'
```

Attendu : `sail-8.5-custom/app` < 500 MB, `node` (alpine) < 80 MB.

- [ ] **Step 10 : Commit**

```bash
# Pas de fichiers à stager — les modifications sont dans les tasks précédentes.
# Ce commit valide que le setup est fonctionnel.
git commit --allow-empty -m "chore(docker): verify optimized dev setup works end-to-end"
```

---

## Task 7 : Mettre à jour la documentation

**Files:**
- Modify: `README.md` (racine du repo)
- Modify: `reservationApp/CLAUDE.md`

### 7a — `reservationApp/CLAUDE.md`

- [ ] **Step 1 : Remplacer la section "Commandes"**

Trouver le bloc :

```markdown
## Commandes

```bash
# Développement (deux terminaux)
php artisan serve          # Laravel sur http://localhost:8000
npm run dev                # Vite HMR sur http://localhost:5173

# Avec Docker/Sail
./vendor/bin/sail up -d
./vendor/bin/sail npm run dev

# Tests
npm test                   # vitest (jsdom, @testing-library/react)
npm run build              # Build production → public/build/
```
```

Le remplacer par :

````markdown
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
````

### 7b — `README.md` (racine)

- [ ] **Step 2 : Ajouter une section "Web App — Dev Docker" après la section "Admin Dashboard"**

Trouver la fin de la section "Admin Dashboard" :

```markdown
via `setRobotStatusProvider()`.
```

Ajouter après :

```markdown

## Web App — Dev Docker

L'application web (`reservationApp/`) tourne sous Docker via Laravel Sail avec une configuration custom allégée.

**Architecture des services :**

| Service | Image | URL |
|---|---|---|
| `laravel.test` | php:8.5-cli-bookworm (custom) | http://localhost |
| `vite` | node:24-alpine | http://localhost:5173 |
| `mysql` | mysql:8.4 | localhost:3306 |

**Démarrage :**

```bash
cd reservationApp
./vendor/bin/sail up -d

# Premier démarrage uniquement
./vendor/bin/sail composer install
docker compose exec vite npm install
```

**Commandes npm** (node absent du conteneur PHP) :

```bash
docker compose exec vite npm install <package>
docker compose exec vite npm run build
```

Voir `reservationApp/CLAUDE.md` pour le détail complet des commandes.
```

- [ ] **Step 3 : Commit**

```bash
git add README.md reservationApp/CLAUDE.md
git commit -m "docs: update docker dev commands for split php/vite services"
```
