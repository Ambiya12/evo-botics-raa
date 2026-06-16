# Robot Admin — architecture (pages + sidebar)

## Vue d'ensemble

Section admin du robot servie sous `/admin/robot/*` (routes `admin.robot.*`, middleware
`auth` + `verified`). Le robot est piloté **directement depuis le navigateur** (pas via Laravel) :
WebSocket rosbridge (`ws://<ip>:9090`) + flux caméra MJPEG (`http://<ip>:8080`).

## Connexion partagée (layout persistant)

`Layouts/RobotLayout.tsx` est un **layout Inertia persistant** : il monte une seule fois
`RobotProvider` (Context). La connexion (`useRosBridge`), la télémétrie (`useRobotTelemetry`),
la config et les commandes y vivent → naviguer entre pages **ne reconnecte pas**.

```
RobotLayout (persistant)
└── RobotProvider (Context partagé)
    └── AuthenticatedLayout (header = RobotHeader)
        └── RobotSidebar + <main>{page}</main>
```

## Pages (sidebar)

| Page | Route | Rôle |
| --- | --- | --- |
| Overview | `admin.robot.overview` (`/admin/robot`) | Lecture seule : santé, caméra, carte, bras |
| Navigation | `admin.robot.navigation` | Carte cliquable, waypoints, actions Nav2 |
| Teleop | `admin.robot.teleop` | Contrôle manuel `/cmd_vel` |
| Arm | `admin.robot.arm` | Contrôle bras `/arm6_joints` + état |
| Diagnostics | `admin.robot.diagnostics` | Capteurs, diagnostics, logs |
| Connection | `admin.robot.connection` | Config IP/ports/caméra |

## Couches

- `Components/Robot/transforms.ts` — transformations ROS pures.
- `hooks/useRobotTelemetry.ts` — souscriptions + état lecture.
- `Components/Robot/RobotContext.tsx` — `RobotProvider` + `useRobotContext()`.
- `hooks/useRosBridge.ts` — WebSocket rosbridge (contrat `RosApi` dans `Components/Robot/types.ts`).

Panneaux de présentation/commande réutilisés sans changement de props : `RobotHealthCards`,
`CameraPanel`, `MapCanvas` (clic optionnel via `onGoal?`), `ManualControls`, `RobotActionsPanel`,
`ArmControlPanel`, `ArmStateView`, `WaypointList`, `EmergencyStopButton`, `ConnectionStatus`,
`SensorStatusPanel`, `DiagnosticsPanel`, `RobotLogs`, `ConnectionSettings`.

## Hors périmètre (état actuel)

i18n de la section robot ; affichage du « mode » robot ; persistance de la config ; correctifs
des bugs historiques (deps `useEffect` de `ManualControls`, topics d'annulation divergents,
`callService` sans lecture de réponse).
