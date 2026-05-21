# CLAUDE.md — apps/

## Mission

Contient les deux applications qui connectent les opérateurs humains au robot physique : un dashboard admin (frontend) et une API de réservation (backend). Le robot expose ses données via **rosbridge WebSocket (ROS2)** — c'est le point d'intégration central.

## Structure

```
apps/
├── frontend/   ← Dashboard admin React (actif, en mock) — voir apps/frontend/CLAUDE.md
└── backend/    ← API Node.js réservations + notifications (non démarré)
```

## Chemin d'intégration

```
Robot physique (ROS2)
  └── rosbridge WebSocket
        ├── frontend : swapper mockRobotDataProvider → rosbridgeProvider
        │              via setRobotStatusProvider() dans robotStatusService.ts
        └── backend  : interface à définir avant de démarrer le code
```

Le frontend est conçu pour ce swap : **aucun composant ni hook à modifier**, seul le provider change.  
Le backend **ne doit pas démarrer** avant que l'interface rosbridge attendue soit clarifiée (contrat de données, topics ROS2 exposés).

## Conventions

- Les deux apps sont indépendantes — pas de code partagé entre `frontend/` et `backend/` pour l'instant.
- Toute nouvelle intégration robot passe par le provider pattern du frontend ou par le backend, jamais directement dans les composants React.

## Règles importantes

- NE JAMAIS démarrer `backend/` sans avoir défini l'interface rosbridge (topics, format JSON, auth).
- IMPORTANT : l'arrêt d'urgence robot doit réagir en ≤ 1 seconde bout en bout (critère MVP non négociable côté frontend ET futur backend).
