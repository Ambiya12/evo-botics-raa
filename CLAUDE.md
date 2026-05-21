# CLAUDE.md

Evo-Botics RAA est un robot autonome d'accueil pour centres d'affaires (ERP), développé à HETIC par une équipe de 4. Le robot accueille les visiteurs, vérifie les réservations via QR code, les guide vers leur salle et assure une médiation linguistique en temps réel.

## Structure du dépôt

```
evo-botics-raa/
├── apps/
│   ├── frontend/      ← Dashboard admin opérateur (React 18 + TS + Vite) — seul code actif
│   └── backend/       ← API Node.js de réservation/notifications (non démarré)
└── docs/
    ├── BACKLOG.md         ← Backlog priorisé P0/P1/P2
    ├── ROADMAP.md         ← Roadmap 5 phases sur 5 mois
    ├── MVP_DEFINITION.md  ← Périmètre MVP + critères de succès mesurables
    └── cdc-technique.md   ← CDC complet : use cases, architecture, stack, conventions
```

## Stack technique globale

| Couche              | Techno                              | Statut      |
|---------------------|-------------------------------------|-------------|
| OS / Middleware     | Ubuntu 20.04 + ROS2 Humble          | Prévu       |
| Calcul embarqué     | Jetson Orin NX                      | Prévu       |
| STT / TTS           | Whisper (local) + Piper TTS         | Prévu       |
| Traduction / NLU    | Llama ou Gemma (local)              | Prévu       |
| Vision (QR/badge)   | OpenCV                              | Prévu       |
| Navigation autonome | Nav2 + SLAM (LiDAR)                 | Prévu       |
| Contrôle bras       | MoveIt2                             | Prévu       |
| Comm. admin         | rosbridge_suite WebSocket           | Prévu       |
| Backend API         | Node.js (réservations + notifs)     | Non démarré |
| Frontend admin      | React 18 + TypeScript + Vite        | En cours    |

## Conventions d'équipe

- **Langue** : code & commits en anglais, documentation en français.
- **Branches** : `main` (prod stable), `dev` (intégration), `feature/xxx`, `fix/xxx`.
- **Commits** : Conventional Commits (ex: `feat: add qr scanner node`).
- **PR** : review obligatoire par ≥ 1 membre avant merge sur `main`.
- **Python (nodes ROS)** : PEP 8, `snake_case` variables, `PascalCase` classes.

## IMPORTANT

- Ne pas commencer `apps/backend` sans avoir clarifié l'interface rosbridge attendue.
- L'arrêt d'urgence doit réagir en ≤ 1 seconde (critère MVP non négociable).
