# Roadmap Projet – Robot d’Accueil Centre d’Affaires

## Durée totale : 5 mois

Équipe : 4 développeurs

---

## Phase 1 : Setup plateforme (Semaine 1)

- Installation de l’environnement Jetson/ROS2 Humble
- Prise en main du ROSMASTER M3 Pro : test moteurs et bras
- Vérification des capteurs : caméra, LiDAR, micro, écran tactile
- Initialisation des nodes ROS de base et communication ROS2
- Test de la mobilité de base sur le même étage

---

## Phase 2 : MVP accueil & réservation (Semaines 2-4)

- Développement du scan QR code / badge
- Vérification des réservations via backend/API
- Interface utilisateur de base sur écran tactile (confirmation, feedback)
- Tests scénarios : visiteur unique et petits groupes
- Logging pour suivi et debug

---

## Phase 3 : MVP navigation & guidage (Semaines 4-6)

- Intégration Nav2 + SLAM pour navigation autonome
- Pathfinding de A → B vers la salle réservée
- Détection et évitement d’obstacles dynamiques (personnes, objets)
- Guidage de groupes de visiteurs
- Tests parcours complets : détection → vérification → guidage

---

## Phase 4 : Interaction avancée (Semaines 6-8)

- Implémentation de la médiation linguistique complète (STT → traduction → TTS)
- Animation gestuelle du bras pour interaction sociale ou pointer direction
- Notification automatique au personnel pour demandes ou incidents
- Tests multilingues et scénarios interactifs complets

---

## Phase 5 : Stabilisation & démo (Semaine 9)

- Tests end-to-end : accueil, interaction, vérification, guidage, navigation, notifications
- Correction des blocages critiques et optimisation des performances
- Validation des scénarios : visiteur unique et groupes
- Préparation de la démonstration finale fonctionnelle
- Livraison des livrables : code source structuré, CDC technique final, diagrammes UML, tag v0.0.1
