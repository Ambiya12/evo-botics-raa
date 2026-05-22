# CLAUDE.md — evo-botics-raa (racine)

## Mission

Robot autonome d'accueil pour centres d'affaires : scan QR, guidage visiteur, médiation linguistique. Seul `reservationApp/` est actif ; les couches ROS2/embarqué sont planifiées.

## Structure

```
evo-botics-raa/
├── reservationApp/       ← App Laravel 12 + React 18 (Inertia) — seule partie active
├── docs/                 ← BACKLOG.md, ROADMAP.md, MVP_DEFINITION.md, cdc-technique.md
├── scripts/              ← Scripts bootstrap (sprint0_bootstrap.sh)
└── .devcontainer/        ← Devcontainer Docker pour ROS2 (non actif en dev web)
```

## Conventions

- Code & commits en anglais, documentation en français.
- Branches : `main` (stable), `dev` (intégration), `feature/xxx`, `fix/xxx`.
- Commits : Conventional Commits (`feat:`, `fix:`, `chore:`, etc.).
- PR : review ≥ 1 membre avant merge sur `main`.
- Python (ROS2) : PEP 8, `snake_case` variables, `PascalCase` classes.

## Règles importantes

- IMPORTANT : Le backend API Node.js n'existe pas encore — ne pas le créer sans clarifier l'interface rosbridge.
- IMPORTANT : Tout le développement web actif se fait dans `reservationApp/` — voir son propre CLAUDE.md.
- NE JAMAIS merger sur `main` sans review.
- L'arrêt d'urgence doit réagir en ≤ 1 seconde (critère MVP non négociable).
