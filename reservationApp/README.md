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

---

## Télémétrie temps réel (robot connecté)

Le dashboard peut recevoir les données du robot physique (Jetson `10.10.221.115`) via WebSocket.
Le pipeline est : **ROS2 → rosbridge → `robot:listen` → Laravel Reverb → Frontend**.

### Prérequis (une seule fois)

```bash
# Installer le client WebSocket PHP et le package Reverb
./vendor/bin/sail composer require textalk/websocket
./vendor/bin/sail composer require laravel/reverb
./vendor/bin/sail artisan reverb:install
```

### Lancement complet avec télémétrie

```bash
./vendor/bin/sail up -d
```

Cela démarre 6 services : `laravel.test`, `vite`, `mysql`, `reverb`, `robot-listener`, `influxdb`.

| Service | Rôle |
|---|---|
| `reverb` | Serveur WebSocket (`ws://localhost:8080`) |
| `robot-listener` | Lit les topics ROS2 via rosbridge et broadcast via Reverb |
| `influxdb` | Stockage long terme des métriques (`http://localhost:8086`) |

### Vérifier que tout fonctionne

```bash
# Logs du listener rosbridge
docker compose logs -f robot-listener

# Logs Reverb
docker compose logs -f reverb

# Tester un broadcast manuel (sans robot)
./vendor/bin/sail artisan tinker
>>> broadcast(new \App\Events\RobotStatusUpdated([
...   'id' => 'test-robot', 'name' => 'EvoRobot', 'mode' => 'rosbridge',
...   'connectionStatus' => 'connected_ros', 'state' => 'GUIDING',
...   'battery' => 75, 'location' => 'Hall A', 'currentWaypoint' => 'wp-01',
...   'destination' => 'Room 12', 'currentMissionSessionId' => null,
...   'lastIncidentSummary' => '', 'lastUpdate' => '10:00:00',
...   'emergencyStop' => false, 'services' => [],
...   'sentAt' => now()->toIso8601String(),
... ]));

# Vérifier les données dans InfluxDB
curl -H "Authorization: Token dev-token-local" \
  "http://localhost:8086/api/v2/query?org=evo-botics" \
  --data-urlencode 'q=from(bucket:"robot_metrics") |> range(start: -5m)'
```

Ouvrir `http://localhost/admin` — le badge de statut passe de **"Mode simulation"** à **"Robot connecté"** dès que Reverb reçoit le premier message.

### Variables d'environnement clés (`.env`)

```env
BROADCAST_CONNECTION=reverb
REVERB_APP_KEY=robot-echo-key
REVERB_APP_SECRET=robot-echo-secret
REVERB_APP_ID=robot-dashboard
REVERB_HOST=localhost
REVERB_PORT=8080
REVERB_SCHEME=http

ROSBRIDGE_URL=ws://10.10.221.115:9090

INFLUXDB_URL=http://influxdb:8086
INFLUXDB_TOKEN=dev-token-local
INFLUXDB_ORG=evo-botics
INFLUXDB_BUCKET=robot_metrics
```

### Mode mock uniquement (sans robot)

Pour démarrer sans les services temps réel :

```bash
./vendor/bin/sail up -d laravel.test vite mysql
```

Le dashboard reste en mode simulation avec les données mock.

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