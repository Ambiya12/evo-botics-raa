# 📅 Application de Réservation (reservationApp)

Cette application est développée avec **Laravel 12** (PHP) pour la partie Backend et **React** (via Inertia.js et Vite) pour la partie Frontend.

---

## 🛠️ Installation et Configuration Initiale

Commencez par cloner le dépôt puis ouvrez votre terminal et lancez ces commandes :
```bash
cd .\reservationApp\
composer install
```
En attendant que tout s'installe, remplissez les champs DB_DATABASE, DB_USERNAME et DB_PASSWORD du fichier .env.example et renommez le .env.

# Lancement du projet avec Docker

- Ouvrez votre terminal (ouvrir un terminal WSL si vous êtes sur Windows) et exécutez la commande suivante pour lancer Docker et installer l'environnement :
```bash
./vendor/bin/sail up -d
```
- Une fois le conteneur démarré, ouvrez un nouveau terminal et exécutez les commandes suivantes :
```bash
./vendor/bin/sail composer install
./vendor/bin/sail npm install
```
- Générez la clé d'application et migrez la base de données : 
```bash
./vendor/bin/sail artisan key:generate
./vendor/bin/sail artisan migrate
```
- Lancez le projet avec :
```bash
./vendor/bin/sail npm run dev
```

> Le serveur Laravel tourne sur `http://localhost` (port 80 via Sail). Vite écoute sur `http://localhost:5173` pour le hot reload — gardez les deux terminaux ouverts.

---

## Routes disponibles

| Route    | Description                                      |
|----------|--------------------------------------------------|
| `/`      | Page d'accueil / réservation QR code             |
| `/admin` | Dashboard opérateur (React + Inertia, mode mock) |

Le dashboard `/admin` fonctionne sans robot connecté grâce au mode mock. Pour brancher un vrai robot, configurez le provider rosbridge dans `resources/js/services/robotStatusService.ts`.

---

## Démarrage rapide (sans Docker)

Si vous n'utilisez pas Sail, vous pouvez démarrer les serveurs directement :

```bash
# Terminal 1 — serveur Laravel
php artisan serve

# Terminal 2 — serveur Vite (assets React)
npm run dev
```

L'application sera disponible sur `http://localhost:8000`.