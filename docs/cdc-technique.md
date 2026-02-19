# Sprint CDC technique

### 1. Vision

Evo Botics est un robot autonome d’accueil pour centres d’affaires (ex. espaces de coworking, centres d’affaires). Il reçoit et guide des visiteurs, vérifie les réservations, fournit des services d’information via un écran tactile et assure une médiation multilingue en temps réel. L’objectif est d’améliorer l’expérience visiteur, réduire la charge du personnel d’accueil et fiabiliser l’orientation vers les salles de réunion.


### 2. Objectifs et perimetre


####  Objectifs

1. Accueillir et orienter visiteurs et groupes jusqu’à leur salle réservée.
2. Vérifier les réservations via QR code ou badge en < 3 s.
3. Navigation autonome sécurisée sur un même étage (LiDAR + SLAM).
4. Médiation linguistique flexible (STT → traduction → TTS) avec sous-titrage.
5. Interface tactile pour services internes : plan, commandes internes, signalement d’un besoin.
6. Notifications au personnel (push / e-mail / webhook) en cas de demande d’aide ou commande.

#### Non-objectifs

1. Reconnaissance faciale (optionnel, non requis).
2. Déplacements entre étages / escaliers.
3. Manipulation d’objets lourds.
4. Usage extérieur ou surfaces non planes.

#### Personas

- **(Galystan, 24 ans, étudiant étranger)** - arrive pour son premier jour , ne maitrise pas parfaitement la langue local , et dois localiser sa salle de travail 
- **(Jules, 50 ans, homme d’affaires)** - souhaite rejoindre sa salle de réunion le plus rapidement possible


#### 3. Use cases
| ID | Nom | Acteur | But |
| --- | --- | --- | --- |
| UC-01 | Accueil d’un visiteur | Visiteur | Être accueilli automatiquement. |
| UC-02 | Vérification réservation | Visiteur | Scanner un QR code ou badge pour permettre au robot de vérifier la réservation via le backend. |
| UC-03 | Guidage vers une salle | Robot | Accompagner le visiteur jusqu’à la salle réservée en utilisant la navigation autonome sécurisée sur un même étage. |
| UC-04 | Médiation linguistique | Visiteur | Interagir avec le robot dans sa langue grâce à la traduction temps réel (STT → traduction → TTS + sous-titres). |
| UC-05 | Interface tactile | Visiteur | Accéder aux services internes via l’écran (plan des salles, informations, demande d’assistance, commandes internes). |
| UC-06 | Notification personnelle | Robot | Envoyer une notification (email / webhook / push) au personnel en cas de demande d’aide ou situation particulière. |
| UC-07 | Navigation autonome | Robot | Se déplacer de manière autonome en évitant obstacles et personnes grâce au LiDAR et au SLAM. |
| UC-08 | Contrôle à distance | Administrateur | Prendre le contrôle du robot via une interface web en cas d’incident ou blocage. |
| UC-09 | Monitoring robot | Administrateur | Consulter en temps réel l’état du robot (batterie, position, statut navigation, logs système). |
| UC-10 | Mouvements du bras | Robot | Le robot est capable d’utiliser son bras dans toutes les directions possibles. |
| UC-11 | Saisie d’un objet | Robot | Le robot est capable de saisir un petit objet. |

#### UC-04 : Médiation linguistique (détaillé)

Acteurs : Visiteur et Robot
Préconditions : Le visiteur doit être à portée des capteurs audio du robot
Scenario nominal :

1. Le visiteur parle
2. Le robot détecte automatiquement la langue
3. STT → traduction → génération réponse
4. Sous-titrage affiché à l’écran 
5. Réponse vocal via TTS

#### UC-02 : Vérification réservation (détaillé)

Acteurs : Visiteur et Robot
Préconditions : Le visiteur possède une réservation
Scénario nominal :

1. Le robot affiche l’interface de scan
2. Le visiteur scanne son QR code
3. Le robot envoie la réponse
4. La réservation est validée 
5. Le robot propose d’accompagner le visiteur vers la salle


#### 4. Architecture technique

```markdown
[ VISITEUR ]                          [ ADMIN ]
      |                                     |
      v                                     v
+-----+----------+                   +------+-------+
|  Ecran Tactile |                   | Interface    |
+-----+----------+                   | Web (React)  |
      |                              +------+-------+
      |                                     |
      | (Input UI / Audio)                  | (WebSocket)
      v                                     v
+-------------+-----------------------------+-------------------------+
|                  JETSON ORIN NX (ROS2 HUMBLE)                       |
|                                                                     |
| [Node: STT] <----> [Node: TRANSLATION/LLM] <----> [Node: ROSBRIDGE] |
|  (Whisper)          (Llama/Gemma)                (rosbridge_suite)  |
|      |                     |                             |          |
|      | (Cmd)               | (Twist)                     | (Joints) |
|      v                     v                             v          |
| [Node: QR/VISION]    [Node: NAVIGATION]           [Node: ARM]       |
|  (OpenCV)             (Nav2 + SLAM)               (MoveIt2)         |
|                                                                     |
| [Node: TTS (Piper)] [Node: Reservation API] [Node: Notification]    |
| [Node: Gesture Controller] [Node: Grasp Logic]                      |
+-----------+------------------------+----------------------+---------+
            |                        |                      |
            v                        v                      v
         [CAMERA]               [LIDAR/ROUES]          [BRAS 6DOF]
                                                           (PINCE)
```

#### 5. Diagrammes UML

Liens ou contenu des diagrammes (use case, sequence, etat). Au minimum 3.

```markdown
pas encore fait
```

#### 6. Stack technique

| Composant | Techno | Justification |
|-----------|--------|---------------|
| OS / Middleware | Ubuntu 20.04 + ROS2 Humble | Base stable et standard pour l’intégration robotique. |
| Calcul embarqué | Jetson Orin NX | Exécution locale des traitements IA (voix, vision, navigation). |
| STT / TTS | Whisper (local) + Piper TTS | Pipeline vocal multilingue hors-ligne, cohérent avec la médiation linguistique. |
| Traduction / NLU | Llama ou Gemma (local) | Traduction temps réel et génération de réponses contextualisées. |
| Vision (QR) | OpenCV | Lecture de QR code/badge pour la vérification de réservation. |
| Navigation autonome | Nav2 + SLAM | Planification locale et déplacement sécurisé sur un même étage. |
| Contrôle bras | MoveIt 2 | Planification cinématique, contrôle joints et sécurité des mouvements. |
| Communication admin | React + rosbridge_suite (WebSocket) | Supervision et contrôle à distance depuis l’interface web. |
| Services backend | API Réservation + Email/Webhook | Validation de réservation et notifications au personnel. |


#### 7. Risques et contraintes

| Risque | Probabilite | Impact | Mitigation |
|--------|-------------|--------|------------|
| Latence de traitement vocal/traduction (> 3 s) | Moyenne | Élevé | Optimiser le pipeline STT → LLM → TTS, utiliser des modèles compacts et du cache de prompts. |
| Erreurs de reconnaissance en environnement bruyant | Haute | Élevé | Micro directionnel, réduction de bruit, confirmation utilisateur à l’écran avant action critique. |
| Échec de lecture QR / badge | Moyenne | Moyen | Ajustement caméra/éclairage, zone de scan guidée UI, tentative manuelle assistée. |
| Dérive navigation / évitement obstacle | Moyenne | Élevé | Calibration LiDAR, tests de trajectoires, zones interdites et fallback arrêt sécurisé. |
| Collision ou mouvement non souhaité du bras | Basse | Élevé | Contraintes MoveIt2, limites articulaires, vitesse réduite et bouton d’arrêt d’urgence admin. |
| Dépendance à un robot unique (point de défaillance) | Moyenne | Élevé | Plan de test en simulation, maintenance préventive, pièces critiques de rechange. |

### Contraintes
- Délai : Livraison du MVP avant la fin du module.
- Équipe : 4-5 développeurs, niveaux hétérogènes en ROS2/IA embarquée.
- Matériel : Un seul robot (ROSMASTER M3 Pro + Jetson Orin NX), disponibilité limitée.
- Environnement : Usage intérieur uniquement, sol plat, même étage (pas d’escaliers/ascenseurs).


#### 8. Conventions d'équipe

**Langue**
- **Code & Commits** : Anglais.
- **Documentation** (CDC, README) : Français.

**Environnement Git**
- `main` : Production stable.
- `dev` : Intégration.
- `feature/xxx` : Développement par fonctionnalité (ex: `feature/navigation`).

**Versioning & Release**
- **Branches** : `feature/feature-name` (ex: `feature/reservation-api`) et `fix/bug-name`.
- **Commits** : Conventional Commits en anglais (ex: `feat: add qr scanner node`).
- **Pull Requests** : Pas de merge direct sur `main`; review obligatoire par au moins 1 membre.
- **Tags** : Tag à chaque version stable (ex: `v1.0.0`).
- **Changelog** : Fichier `CHANGELOG.md` maintenu à chaque release.

**Code Style**
- **Python (ROS Nodes)** : Standard PEP 8.
  - Variables : `snake_case`
  - Classes : `PascalCase`
- **Commentaires** : En anglais dans le code.

**Organisation & Communication**
- **Sprint** : 2 à 3 semaines.
- **Daily Meeting** : "Ce que j'ai fait", "Ce que je vais faire", "Bloquants".
- **Discord** : Groupe `evo-botics` pour le partage de ressources techniques.


#### 9. Roadmap et questions ouvertes

Planning macro prévisionnel.

| Phase | Semaines | Objectif |
|-------|----------|----------|
| 1. Setup plateforme | Semaine 1 | Installation environnement Jetson/ROS2, validation capteurs (caméra, LiDAR, audio) et base de mobilité. |
| 2. MVP accueil & réservation | Semaines 2-4 | Parcours visiteur: accueil, scan QR/badge, vérification réservation via API, retour UI. |
| 3. MVP navigation & guidage | Semaines 4-6 | Navigation autonome (Nav2 + SLAM), guidage vers salle, évitement d’obstacles. |
| 4. Interaction avancée | Semaines 6-8 | Médiation linguistique complète (STT → traduction → TTS), gestes bras et notifications personnel. |
| 5. Stabilisation & démo | Semaine 9 | Tests de bout en bout, correction des blocages critiques, scénario final de démonstration. |

### Questions ouvertes
- [ ] Quelle est l'autonomie réelle du ROSMASTER M3 Pro avec la Jetson à pleine charge ?
- [ ] Le micro intégré est-il suffisant en environnement bruyant ou faut-il un micro externe ?
- [ ] Comment gérer la latence entre la reconnaissance vocale et la réponse du robot pour que ce soit naturel ?
