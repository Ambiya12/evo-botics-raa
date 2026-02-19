# Roadmap Projet – Robot d’Accueil Centre d’Affaires

## Durée totale : 5 mois

Équipe : 4 développeurs

---

## Phase 1 : Setup et préparation (Semaine 1)

- Installation Ubuntu 20.04 + ROS2 Humble sur Jetson Orin
- Prise en main du ROSMASTER M3 Pro
- Tests moteurs et bras via terminal
- Vérification capteurs : LiDAR, caméra, écran tactile

---

## Phase 2 : Modules Core – Interaction et Navigation (Semaines 2-3)

### Interaction & Médiation linguistique

- Implémentation `voice_node` STT local (Whisper tiny/base)
- Traduction temps réel via `translate_node` ou LLM
- Synthèse vocale offline (PiperTTS)
- Sous-titrage et affichage sur interface tactile

### Navigation

- Configuration Nav2 : map, costmap, footprint, inflation radius
- Tests SLAM avec LiDAR
- Déplacement autonome de test, évitement obstacles
- Pathfinding de A → B

---

## Phase 3 : Vérification et Guidage (Semaines 4-5)

- Implémentation `vision_node` pour scan QR / badge
- Vérification réservation avec backend simulé / réel
- Intégration guidage vers salle via Nav2
- Gestion des groupes de visiteurs
- Tests de flux complet : détection → vérification → guidage

---

## Phase 4 : Interface tactile & Services internes (Semaines 6-7)

- Développement UI écran tactile (`ui_node` React)
- Accès aux informations du centre (plan, services)
- Commandes internes et signalement d’assistance
- Intégration avec notifications au personnel (`notify_node`)

---

## Phase 5 : Administration & Monitoring (Semaines 8)

- Interface admin web pour contrôle à distance (`admin_node`)
- Monitoring robot : batterie, position, logs, statut navigation
- Implémentation du bouton d’arrêt d’urgence et watchdog

---

## Phase 6 : Tests intégrés & Optimisation (Semaines 9)

- Tests end-to-end : accueil, interaction, vérification, guidage, navigation
- Simulation collisions et sécurité via EmergencyStop
- Optimisation latence STT / TTS
- Ajustement navigation (vitesse, costmap, clearance)

---

## Phase 7 : Démonstration finale & Livrables (Semaine 10)

- Présentation complète fonctionnelle aux enseignants
- Validation scénarios : visiteur unique / groupe
- Livraison des livrables :
  - Code source structuré
  - CDC technique final
  - Tag v0.0.1
  - Documentation et diagrammes UML
