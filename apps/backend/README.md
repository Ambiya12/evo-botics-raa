# Application de Réservation

Cette application est maintenant séparée en deux dossiers :

| Partie | Dossier | Rôle |
|---|---|---|
| Backend | `apps/backend` | Laravel 12, routes, API, auth, base de données |
| Frontend | `apps/frontend` | React, TypeScript, Vite, Tailwind |

La connexion reste assurée par **Inertia.js** et **Laravel Vite** : Laravel sert les routes et le shell Blade, Vite compile `../frontend/src/app.tsx` vers `public/build`.

---

## 🛠️ Installation et Configuration Initiale

Commencez par cloner le dépôt puis ouvrez votre terminal et lancez ces commandes :
```bash
cd apps/backend
composer install
cd ../frontend
npm install
```
En attendant que tout s'installe, copiez `apps/backend/.env.example` vers `apps/backend/.env`, puis remplissez `DB_DATABASE`, `DB_USERNAME` et `DB_PASSWORD`.

# Lancement du projet avec Docker

- Ouvrez votre terminal (ouvrir un terminal WSL si vous êtes sur Windows) et exécutez la commande suivante pour lancer Docker et installer l'environnement :
```bash
cd apps/backend
./vendor/bin/sail up -d
```
- Une fois le conteneur démarré, ouvrez un nouveau terminal et exécutez les commandes suivantes :
```bash
./vendor/bin/sail composer install
docker compose exec vite npm install
```
- Générez la clé d'application et migrez la base de données : 
```bash
./vendor/bin/sail artisan key:generate
./vendor/bin/sail artisan migrate
```

> Le serveur Laravel tourne sur `http://localhost` (port 80 via Sail). Vite écoute sur `http://localhost:5173` uniquement pour le hot reload — gardez les deux terminaux ouverts.

Ouvrez le dashboard ici :

```text
http://localhost/admin
```

N'ouvrez pas `http://localhost:5173` directement : c'est seulement le serveur Vite, pas l'application Laravel.

---

## Routes disponibles

| Route    | Description                                      |
|----------|--------------------------------------------------|
| `/`      | Page d'accueil / réservation QR code             |
| `/admin` | Dashboard opérateur (React + Inertia, mode mock) |

Le dashboard `/admin` fonctionne sans robot connecté grâce au mode mock. Pour brancher un vrai robot, configurez le provider rosbridge dans `../frontend/src/services/robotStatusService.ts`.

---

## Démarrage rapide (sans Docker)

Si vous n'utilisez pas Sail, vous pouvez démarrer les serveurs directement :

```bash
# Terminal 1 — serveur Laravel
cd apps/backend
php artisan serve

# Terminal 2 — serveur Vite (assets React)
cd apps/frontend
npm run dev
```

L'application sera disponible sur `http://localhost:8000`.

Ouvrez le dashboard ici :

```text
http://localhost:8000/admin
```

Si vous voyez une page "Laravel + Vite", vous êtes sur le serveur Vite (`localhost:5173`) au lieu de la route Laravel `/admin`.
