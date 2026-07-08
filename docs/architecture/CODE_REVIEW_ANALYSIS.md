# Analyse Complète du Package `evo_ws` — Préparation Code Review

---

## 1. TYPES DE BUILD DES PACKAGES

| Package | Système de Build | Raison |
|----------|-------------------|--------|
| `evo_reception_interfaces` | **`ament_cmake`** | Définitions d'interfaces ROS2 pures (`.msg`, `.srv`, `.action`) — doit utiliser CMake car `rosidl_generate_interfaces` l'exige |
| `evo_navigation` | **HYBRIDE** (`ament_cmake` + `ament_cmake_python`) | Mélange de nœuds C++ (`cmd_vel_safety_gate.cpp`, `cmd_vel_output_relay.cpp`, `navigation_goal_validator.cpp`) et de logique de navigation Python. Le C++ est nécessaire pour la sécurité des mouvements à faible latence. Python pour l'orchestration flexible et la configuration YAML |
| `evo_reception` | **`ament_python`** | Python pur — machine d'état, intégration QR, appels HTTP. Aucun besoin de performances C++ |
| `evo_vision` | **`ament_python`** | Python wrap OpenCV + pyzbar. Ces bibliothèques sont nativement Python, pas besoin de compilation C++ |
| `evo_voice` | **`ament_python`** | Python wrap faster-whisper, SpeechRecognition, Piper TTS. Toutes des bibliothèques Python |
| `evo_web` | **`ament_python`** | Serveur HTTP Python pur, relais de bras. Assez simple pour Python |

### Pourquoi HYBRIDE pour evo_navigation ?

Le fichier `CMakeLists.txt` (`evo_navigation/CMakeLists.txt:16`) utilise `ament_python_install_package()` en parallèle de `add_executable()` pour les nœuds C++. C'est nécessaire car :

- **C++** pour `cmd_vel_safety_gate` (vérifications d'arrêt d'urgence à la fréquence des capteurs), `navigation_goal_validator` (validation géométrique avec les actions Nav2). Ces nœuds doivent être rapides et déterministes.
- **Python** pour `navigation_orchestrator.py` (logique de waypoints, config YAML), qui bénéficie d'une itération rapide et n'a pas besoin de latence < 1 ms.

### Pourquoi PAS les alternatives ?

- **evo_navigation en Python pur** : Perdrait les vérifications de sécurité à faible latence. `cmd_vel_safety_gate` doit traiter les commandes de vitesse au rythme des données capteurs — le GIL de Python serait un goulot d'étranglement.
- **evo_navigation en CMake pur** : Rendraient la configuration des waypoints, le parsing YAML et la logique d'orchestration plus difficiles à maintenir et tester.
- **evo_reception en CMake** : Overkill. La machine d'état de dialogue et les appels HTTP vers l'API backend ne bénéficient pas de la vitesse du C++. `urllib` + `dataclasses` de Python sont parfaitement adéquats.

---

## 2. TOUS LES NŒUDS ET LEURS FONCTIONS

### Package evo_reception (entry_points dans `setup.py`, `src/evo_reception/setup.py:23-28`)

| Nœud | Fichier | Fonction |
|------|---------|----------|
| **`dialogue_manager_node`** | `dialogue_manager_node.py` | Cerveau central. Exécute la machine d'état qui gère l'accueil du visiteur : accueil → intention → scan QR → validation → navigation. S'abonne aux topics de vision (présence), voix (intention) et QR (détections). Appelle le service de validation QR. Déclenche la navigation via l'action GuideToDestination |
| **`qr_reservation_bridge_node`** | `qr_reservation_bridge_node.py` | Pont entre ROS2 et l'API backend Laravel externe. Expose le service `ValidateQr` → appelle le backend via HTTP POST → traduit les réponses HTTP en résultats ROS2 (VALID/INVALID/EXPIRED/DUPLICATE/UNAVAILABLE) |
| **`mock_guide_action_server`** | `mock_guide_action_server.py` | Navigation simulée pour les tests/développement. Simule l'action GuideToDestination en attendant au lieu de déplacer le robot. Accepte tout goal, retourne ARRIVED après un délai configurable |

### Package evo_navigation (CMakeLists.txt:18-50)

| Nœud | Fichier | Langage | Fonction |
|------|---------|---------|----------|
| **`navigation_orchestrator_node`** | `navigation_orchestrator_node.py` | Python | Serveur d'action de navigation réelle. Implémente GuideToDestination en utilisant Nav2 Navigator. Vérifie l'e-stop, la localisation (AMCL) et la disponibilité de Nav2 avant d'accepter les goals. Utilise `NavigationOrchestrator` avec `Nav2Navigator` |
| **`cmd_vel_safety_gate`** | `cmd_vel_safety_gate.cpp` | C++ | Bloque les commandes de vitesse quand l'e-stop est actif. Sécurité à faible latence au niveau du driver |
| **`cmd_vel_output_relay`** | `cmd_vel_output_relay.cpp` | C++ | Relaie les commandes de vitesse entre les topics. Permet le remapping de topics sans toucher aux drivers |
| **`navigation_goal_validator`** | `navigation_goal_validator.cpp` | C++ | Valide les goals Nav2 avant de les transmettre. Vérifie la grille d'occupation et les transformations TF |

### Package evo_vision

| Nœud | Fichier | Fonction |
|------|---------|----------|
| **`qr_scanner_node`** | `qr_scanner_node.py` | Lit les images de la caméra, décode les QR codes (pyzbar ou OpenCV QUIRC), publie les événements de détection en JSON sur `/vision/qr/detections` |
| **`human_approach_node`** | `human_approach_node.py` | Détection de personnes + logique d'approche. Publie les messages PersonApproach et présence (Bool) |
| **`depth_obstacle_scan_node`** | `depth_obstacle_scan_node.py` | Détection d'obstacles basée sur la profondeur |
| **`object_detector_node`** | `object_detector_node.py` | Pipeline de détection d'objets |

### Package evo_voice

| Nœud | Fichier | Fonction |
|------|---------|----------|
| **`intent_detector_node`** | `intent_detector_node.py` | Classifie le texte transcrit en intentions (affirmative, negative, reservation, cancel, etc.) en utilisant des patterns YAML |
| **`stt_node`** | `stt_node.py` | Speech-to-text utilisant faster-whisper/speechrecognition |
| **`tts_node`** | `tts_node.py` | Text-to-speech utilisant Piper TTS avec une file d'attente |

### Package evo_web

| Nœud | Fichier | Fonction |
|------|---------|----------|
| **`web_server_node`** | `web_server_node.py` | Serveur HTTP (port 8080). Sert le dashboard + flux MJPEG caméra + snapshot. S'abonne à `/camera/color/image_raw`, encode en JPEG, sert via les endpoints HTTP |
| **`arm_command_relay_node`** | `arm_command_relay_node.py` | Relaie les commandes de bras du navigateur (via rosbridge → `/evo/arm/command`) vers le driver du robot (`/arm6_joints`). Limite les valeurs dans les plages articulaires |

---

## 3. COMMENT LES NŒUDS COMMUNIQUENT AVEC LE BACKEND ET LE FRONTEND

### Robot → Backend (Flux de Validation QR)

```
Caméra → qr_scanner_node.py (:177 /vision/qr/detections)
  → dialogue_manager_node.py (:126 subscription, :222 on_qr_detection)
    → Appel service ValidateQr (:247 call_async)
      → qr_reservation_bridge_node.py (:114 on_validate_qr → :128 perform_validation)
        → HTTP POST vers le backend Laravel (:136-138 post_json avec qr_payload)
        ← Le backend répond {status: "success", data: {destination_id, uuid, ...}}
```

### Robot → Frontend (Dashboard)

```
rosbridge_server (pont WebSocket sur le port 9090)
  → Le dashboard admin Laravel (/admin/robot) se connecte via ws://robot-ip:9090
  → Peut s'abonner aux topics : /reception/dialogue/state, /reception/workflow/status
  → Peut publier des commandes de bras sur /evo/arm/command

Caméra → web_server_node.py (:131 on_image)
  → Encode en JPEG (:240 _encode_to_jpeg)
  → Servi sur /camera/stream (MJPEG) et /camera/snapshot
  → index.html (:1) montré comme référence ; le vrai dashboard est Laravel /admin/robot
```

### Frontend → Robot (Contrôle du Bras)

```
Navigateur → rosbridge WebSocket → /evo/arm/command (ArmJoints)
  → arm_command_relay_node.py (:30 publisher → :34 subscription)
    → Limite les valeurs articulaires (:44-50 JOINT_LIMITS)
    → Publie sur /arm6_joints (topic du driver robot)
```

### Publication du Statut du Workflow

`dialogue_manager_node.py:363` publie `WorkflowStatus` sur `/reception/workflow/status` avec `session_id`, `state`, `outcome`, `detail`, `destination_id`. Utilise la QoS TRANSIENT_LOCAL pour que les abonnés tardifs (comme le dashboard) reçoivent le dernier statut immédiatement.

---

## 4. 8 FICHIERS CLÉS — ANALYSE DÉTAILLÉE

### FICHIER 1 : `dialogue_manager.py` (387 lignes)

**Pourquoi important** : C'est la **machine d'état pure** — le cerveau du robot. Zéro dépendance ROS. Toutes les transitions d'état sont déterministes et testables sans aucune infrastructure ROS.

**Ce qu'il fait** :
- `DialogueState` enum (10 états) : IDLE → PRESENCE_ARMED → GREETING → WAITING_FOR_INTENT → WAITING_FOR_QR → VERIFYING_QR → READY_TO_GUIDE → NAVIGATING → ARRIVED → ERROR
- `DialogueEvent` enum (16 événements) : visitor_approached, qr_detected, tts_completed, navigation_arrived, etc.
- `DialogueManager` : Consomme les intentions et événements, produit des `Transition` (état précédent, nouvel état, accepté, phrases vocales)
- Utilise des **tables de dispatch** (`_INTENT_TRANSITIONS`, `_EVENT_TRANSITIONS`) — dictionnaires mappant `(state, event)` → fonctions handler — au lieu d'énormes chaînes if/elif

**Est-ce propre ?** Oui. Le pattern de table de dispatch (`dialogue_manager.py:369`) rend l'ajout de nouvelles transitions trivial. Chaque handler est une fonction autonome. Le dataclass `Transition` est immuable.

**Dépendances** : Uniquement `dataclasses`, `enum`, `typing` — stdlib seulement. Utilise `evo_reception.qr_integration.QrValidationOutcome` pour le typage.

**Pourquoi PAS les alternatives** : Ne pas utiliser la bibliothèque `transitions` (bibliothèque de machine d'état Python) car elle ajoute une surcharge de dépendance et les déploiements ROS2 Humble sur Jetson sont sensibles aux dépendances. L'implémentation personnalisée fait 387 lignes — utiliser un framework pour cela serait plus de code que le problème.

---

### FICHIER 2 : `dialogue_manager_node.py` (419 lignes)

**Pourquoi important** : L'**adaptateur ROS2** qui relie la machine d'état pure aux topics, services et actions ROS2. C'est ici que toutes les entrées/sorties se produisent.

**Ce qu'il fait** :
- Lignes 39-134 : `__init__` déclare 16+ paramètres ROS, crée les publishers/subscribers/clients/action clients, initialise tous les helpers
- `on_intent` (136) : Reçoit l'intention de `/voice/intent/result`, délègue à `manager.handle_intent()`
- `on_person_approach` (145) : Vision → événement de présence
- `on_tts_status` (165) : Suit le cycle de vie TTS pour déclencher les événements `TTS_COMPLETED`. Définit le flag `tts_ready`, libère les salutations différées
- `on_qr_detection` (222) : Gate de scan QR → appel service ValidateQr → callback asynchrone
- `_on_qr_validation` (252) : Gère la réponse de validation QR asynchrone, mappe l'enum de résultat, vérifie les destinations autorisées
- `apply` (328) : Méthode centrale — publie l'état, publie les phrases TTS, publie le statut du workflow, gère le nettoyage entre les états
- `on_timer` (296) : Vérificateur de délais pour les timeouts

**Patterns de conception clés** :
- **Pattern de jeton de requête** (`qr_request_token`) : Empêche les callbacks asynchrones obsolètes d'affecter la session en cours
- **Salutation différée** (`DeferredGreeting`) : Gère la condition de course où le TTS n'est pas prêt quand un visiteur arrive

**Pourquoi PAS les alternatives** : Ne pas utiliser ROS2 `LifecycleNode` — le dialogue manager n'est pas un driver matériel, c'est un orchestrateur de haut niveau. Utiliser un Managed Node ajouterait une complexité inutile.

---

### FICHIER 3 : `qr_integration.py` (170 lignes)

**Pourquoi important** : Logique métier pure pour le scan QR. Zéro dépendance ROS. Contient la classe `QrScanGate` qui empêche les scans QR dupliqués/en concurrence.

**Ce qu'il fait** :
- `QrValidationOutcome` enum (5 états) : VALID, INVALID, EXPIRED, DUPLICATE, UNAVAILABLE
- `ScanDecision` enum (5 états) : ACCEPTED, IGNORED_STATE, INVALID, DUPLICATE, BUSY
- `QrScanGate` (126) : Protège contre les scans dupliqués (même contenu dans la période de cooldown), les validations concurrentes (état BUSY pendant un scan en cours), et n'accepte les scans que lorsque le dialogue est en état WAITING_FOR_QR
- `extract_decoded_text` (78) : Extrait le texte des événements JSON bruts ou du texte brut — découple le format du scanner de la logique métier
- `validate_backend_configuration` (52) : Valide la configuration de l'URL backend au démarrage (doit être HTTPS, pas de credentials dans l'URL)
- `_ensure_outcome_mapping` (15) : Mapping lazy de `QrValidationOutcome` → constantes ROS2 `ValidateQr.Response` — évite les imports circulaires

**Pourquoi PAS les alternatives** : Ne pas utiliser un broker de messages (RabbitMQ) pour le traitement QR — c'est un système temps réel mono-robot où les topics ROS2 sont le bus de messages. Ajouter un broker séparé ajouterait une infrastructure inutile.

---

### FICHIER 4 : `qr_reservation_bridge_node.py` (313 lignes)

**Pourquoi important** : Le **pont entre ROS2 et le backend Laravel externe**. C'est ici que le robot parle au cloud.

**Ce qu'il fait** :
- Expose le **service** ROS2 `ValidateQr` (pas un topic) sur `/reception/qr/validate`
- `perform_validation` (128) : HTTP POST vers le backend → parse la réponse → retourne `BridgeValidation` avec outcome, message, destination_id, données de réservation
- Gestion d'erreurs : HTTPError (400/404/422 avec codes d'erreur spécifiques), TimeoutError, URLError — chacun mappe vers un `QrValidationOutcome` spécifique
- `destination_id_from_response` (234) : Extrait la destination de multiples chemins JSON possibles (`body.destination_id`, `data.destination_id`, `data.room_id`)
- `reservation_from_response` (255) : Normalise les données de réservation en un dict cohérent
- `publish_status` (269) : Publie le statut de validation en JSON sur `/reception/qr/status` — utilisé par le dashboard pour le feedback UI
- Utilise `ThreadPoolExecutor` (82) pour éviter de bloquer le thread spin ROS2 pendant les appels HTTP

**Dépendances** : Uniquement stdlib (`urllib`, `json`, `concurrent.futures`, `dataclasses`). Pas de bibliothèque `requests` — évite une dépendance supplémentaire. `urllib.request` est suffisant pour un seul endpoint POST.

**Pourquoi PAS `requests`** : Le déploiement Jetson est sensible aux dépendances. `urllib` est intégré, coût d'installation zéro. Pour un seul POST, `requests` n'ajouterait rien.

---

### FICHIER 5 : `qr_scanner_node.py` (231 lignes)

**Pourquoi important** : Pipeline Caméra → Détection QR. Détecte les QR codes de la caméra du robot et les publie comme messages ROS2.

**Ce qu'il fait** :
- Supporte **deux backends** : `pyzbar` (préféré, wrapper Python pour libzbar) et OpenCV QUIRC (fallback, nécessite une build OpenCV spécifique)
- `selected_backend` (108) : Logique d'auto-détection → pyzbar > OpenCV > None
- `on_image` (121) : Limite le taux de scan (`min_scan_interval_sec`), redimensionne l'image si nécessaire, décode le QR, applique un cooldown sur la même valeur QR, publie les événements de détection en JSON
- `decode_qr` (180) : `pyzbar` : convertit en niveaux de gris → décode. `opencv` : utilise `cv2.QRCodeDetector.detectAndDecode()`
- Les événements de détection incluent : `decoded_text`, `stamp`, `camera_topic`, `decoder_backend`, `is_json`, `parsed_type`, `has_uuid` — métadonnées riches pour les nœuds en aval

**Dépendances** : `cv2` (opencv-python), `pyzbar`, `libzbar0`. OpenCV est aussi utilisé pour la conversion/redimensionnement d'image.

**Pourquoi pyzbar plutôt que le détecteur QR d'OpenCV** : pyzbar utilise libzbar qui est plus fiable pour les QR codes sous différents angles/distances. Le backend QUIRC d'OpenCV est un fallback car il nécessite une build OpenCV personnalisée sur Jetson.

---

### FICHIER 6 : `web_server_node.py` (286 lignes)

**Pourquoi important** : Sert le **dashboard HTTP** et le **flux caméra** au navigateur. C'est ainsi que le frontend voit le robot.

**Ce qu'il fait** :
- `CameraSnapshotHandler` (28) : Étend `SimpleHTTPRequestHandler` avec 3 routes personnalisées :
  - `/camera/snapshot` (55) : Retourne une seule image JPEG
  - `/camera/stream` (81) : Flux MJPEG avec boundary `multipart/x-mixed-replace`
  - `/camera/status` (70) : Statut JSON avec compteur d'images, info d'encodage, erreurs
- `WebServerNode` (131) : S'abonne au topic caméra, encode les images en JPEG à FPS/qualité/largeur configurables. Buffer JPEG thread-safe avec `threading.Lock`
- `on_image` (186) : Décode le message ROS2 `Image` → redimensionne si nécessaire → encode en JPEG → stocke dans `latest_jpeg` avec compteur de séquence
- `get_jpeg` (248) : Getter thread-safe retournant un tuple `(seq, jpeg_bytes)`
- Sert les fichiers statiques (index.html) depuis le répertoire installé `share/evo_web/web/`

**Dépendances** : `opencv-python` pour le traitement d'image, `numpy` pour la manipulation de tableaux. Utilise stdlib `http.server` (PAS Flask/FastAPI).

**Pourquoi stdlib http.server plutôt que Flask/FastAPI** : C'est un serveur HTTP à usage unique servant 2-3 endpoints. Flask ajouterait ~20 dépendances. Le pattern de streaming MJPEG (multipart chunked) fonctionne parfaitement avec `http.server` brut. Aucun framework de routage nécessaire.

---

### FICHIER 7 : `navigation_orchestrator.py` (252 lignes)

**Pourquoi important** : **Logique d'orchestration de navigation pure** avec zéro dépendance ROS. Contient `Nav2Navigator` qui enveloppe le client d'action Nav2.

**Ce qu'il fait** :
- `NavigationOrchestrator.execute` (116) : Verrou d'exécution unique, vérifications de portes (e-stop, localisation, disponibilité Nav2), recherche de waypoint, délégation au navigateur
- `Nav2Navigator.navigate` (183) : Envoie le goal d'action `NavigateToPose` avec timeout et support d'annulation. Attente en deux phases : acceptation du goal → résultat
- `NavigationGates` (51) : Triple vérification de sécurité — estop_active, localization_ready, nav2_ready
- `localization_is_ready` (67) : Vérification de localisation AMCL avec timeout configurable. Important : un timeout de 0 signifie "la dernière pose connue est valide" — car AMCL ne republie pas quand le robot est stationnaire
- `Navigator` Protocol (92) : Interface pour les backends de navigation. L'implémentation actuelle est `Nav2Navigator`, mais le protocol permet de substituer un navigateur mock pour les tests

**Dépendances** : `math`, `time`, `dataclasses`, `threading`, `typing.Protocol` — tout stdlib. `rclpy.action`, `nav2_msgs` pour le Nav2Navigator.

**Pourquoi PAS utiliser NavigateToPose de ROS2 directement** : L'orchestrateur ajoute des portes de sécurité (vérification e-stop, vérification localisation) que Nav2 ne fournit pas. Ces vérifications se font côté robot, pas dans le BT navigator de Nav2.

---

### FICHIER 8 : `navigation_orchestrator_node.py` (266 lignes)

**Pourquoi important** : Le **nœud ROS2** qui enveloppe `NavigationOrchestrator` et l'expose comme serveur d'action `GuideToDestination`. C'est ce que le dialogue manager appelle pour démarrer la navigation.

**Ce qu'il fait** :
- `__init__` (31) : Charge les waypoints depuis YAML, valide la configuration de navigation, s'abonne aux topics e-stop et localisation, crée le serveur d'action
- `current_gates` (149) : Évaluation dynamique des portes — vérifie la disponibilité du serveur Nav2 + le statut de localisation AMCL au moment de la requête
- `on_localization` (166) : Parse `PoseWithCovarianceStamped` d'AMCL, vérifie la covariance diagonale (x_variance, y_variance) contre `max_localization_xy_variance`
- `accept_goal` (179) : Un seul goal actif à la fois — rejette si occupé
- `execute_goal` (187) : Délègue à `orchestrator.execute()`, mappe `NavigationOutcome` → `GuideToDestination.Result`, gère succeed/cancel/abort
- `publish_status` (218) : Publie les messages `NavigationStatus` + feedback d'action. Les états d'erreur sont loggés au niveau ERROR
- Utilise `MultiThreadedExecutor` (250) : Nécessaire car les callbacks d'action et de subscription s'exécutent concurremment

---

## 5. FLUX COMPLET DU QR CODE

```
1. CAPTURE CAMÉRA
   Caméra du robot → topic ROS2 /camera/color/image_raw
   
2. DÉTECTION QR
   qr_scanner_node.py (:90 s'abonne à la caméra) 
     → on_image (:121) décode l'image avec pyzbar/OpenCV
     → publie JSON sur /vision/qr/detections (:83, :177)
     Fichiers : src/evo_vision/evo_vision/qr_scanner_node.py
               src/evo_vision/evo_vision/image_utils.py (helper color_image_to_bgr)

3. LE DIALOGUE MANAGER REÇOIT LE QR
   dialogue_manager_node.py (:126 s'abonne à /vision/qr/detections)
     → on_qr_detection (:222) vérifie QrScanGate 
     → accepte seulement si state == WAITING_FOR_QR ET qr_prompt_completed
     → appelle handle_event(QR_DETECTED) pour transitionner vers VERIFYING_QR
     → appelle le service ValidateQr (:247 call_async)
     Fichiers : src/evo_reception/evo_reception/dialogue_manager_node.py
               src/evo_reception/evo_reception/qr_integration.py (QrScanGate, extract_decoded_text)

4. VALIDATION QR (APPEL DE SERVICE)
   qr_reservation_bridge_node.py (:114 on_validate_qr)
     → perform_validation (:128) envoie HTTP POST au backend
     → URL du backend configurée dans reception.launch.py (:11 param validation_url)
     → Le backend répond {status: "success", data: {destination_id, uuid, ...}}
     → Le service répond avec outcome (VALID/INVALID/EXPIRED/DUPLICATE/UNAVAILABLE) + destination_id
     Fichiers : src/evo_reception/evo_reception/qr_reservation_bridge_node.py
               src/evo_reception/launch/reception.launch.py (configuration de lancement)

5. NAVIGATION DÉCLENCHÉE
   dialogue_manager_node.py :252 _on_qr_validation
     → handle_qr_result → si VALID: state = READY_TO_GUIDE
     → TTS termine l'annonce de guidage
     → NavigationDriver.request(destination_id) (:198)
     → Envoie le goal d'action GuideToDestination à /reception/guide_to_destination
     Fichiers : src/evo_reception/evo_reception/dialogue_manager_node.py
               src/evo_reception/evo_reception/_navigation_driver.py (NavigationDriver)

6. EXÉCUTION DE LA NAVIGATION
   navigation_orchestrator_node.py (:131 serveur d'action)
     → accept_goal (:179) 
     → execute_goal (:187) → orchestrator.execute()
     → Nav2Navigator.navigate → action NavigateToPose → le robot se déplace
     → Retourne ARRIVED/CANCELLED/TIMEOUT/FAILED
     Fichiers : src/evo_navigation/evo_navigation/navigation_orchestrator_node.py
               src/evo_navigation/evo_navigation/navigation_orchestrator.py (Nav2Navigator)
               src/evo_reception_interfaces/action/GuideToDestination.action (définition de l'action)

7. MONITORING FRONTEND
   Tout au long : dialogue_manager_node publie sur :
     - /reception/dialogue/state (String) — pour l'affichage d'état du dashboard
     - /reception/workflow/status (msg WorkflowStatus) — session_id, outcome, detail
   Le dashboard reçoit via rosbridge WebSocket sur le port 9090
   Fichiers : src/evo_web/web/index.html (page de référence)
             src/evo_web/launch/web_dashboard.launch.py (lance rosbridge + serveur web)
```

**Fichiers d'interface utilisés** :
- `evo_reception_interfaces/action/GuideToDestination.action` — action de navigation (goal: request_id + destination_id, result: outcome + message, feedback: state)
- `evo_reception_interfaces/srv/ValidateQr.srv` — service de validation QR (request: request_id + qr_payload, response: outcome + destination_id + message)
- `evo_reception_interfaces/msg/WorkflowStatus.msg` — statut dashboard (session_id, state, outcome, detail, destination_id)

---

## 6. ANALYSE SOLID / YAGNI / KISS / DRY

### SOLID

**S - Single Responsibility (Responsabilité Unique)** : Chaque fichier a UNE seule responsabilité claire.
- `dialogue_manager.py` → machine d'état pure. Pas d'I/O.
- `dialogue_manager_node.py` → adaptateur I/O ROS. Pas de logique métier.
- `qr_integration.py` → logique domaine QR. Pas de ROS.
- `qr_reservation_bridge_node.py` → pont HTTP backend. Fait seulement des appels HTTP.

**O - Open/Closed (Ouvert/Fermé)** : Les tables de dispatch de la machine d'état (`_INTENT_TRANSITIONS:284`, `_EVENT_TRANSITIONS:369`) sont des dictionnaires. Ajouter de nouvelles transitions signifie ajouter une paire clé-valeur — aucun code existant modifié.

**L - Liskov Substitution** : Le Protocol `Navigator` dans `navigation_orchestrator.py:92` est une interface claire. `Nav2Navigator` l'implémente. On pourrait substituer `MockNavigator` sans toucher à `NavigationOrchestrator`.

**I - Interface Segregation** : `NavigationDriver` dans `_navigation_driver.py:10` expose seulement `request()` et `cancel()`. Pas un serveur d'action complet — juste ce dont le dialogue manager a besoin.

**D - Dependency Inversion** : Le constructeur de `NavigationOrchestrator` dans `navigation_orchestrator.py:102` reçoit `navigator` et `gates` comme dépendances de constructeur (tous deux sont des callables/Protocols). Il ne les instancie pas. Le nœud dans `navigation_orchestrator_node.py:124` les assemble.

### YAGNI (You Aren't Gonna Need It — Tu n'en auras pas besoin)

- **Pas d'authentification** sur le serveur web — il n'y a pas de scénario multi-utilisateur
- **Pas de base de données** sur le robot — toute la persistance est dans le backend Laravel
- **Pas de framework de logging** — `rclpy.get_logger()` est suffisant pour ROS2
- `mock_guide_action_server.py` est le seul nœud de test — prouve YAGNI pour la production (le vrai est `navigation_orchestrator_node.py`)

### KISS (Keep It Simple, Stupid — Reste Simple)

- `QrScanGate` dans `qr_integration.py:126` : 3 booléens + 1 chaîne + 1 timestamp. Pas de framework complexe de déduplication.
- `TtsStatusTracker` dans `dialogue_manager.py:39` : Suit pending/speaking/completed avec 4 champs.
- `DeadlineController` dans `_deadline_controller.py:9` : deadline + type d'événement. Un seul callback timer.

### DRY (Don't Repeat Yourself — Ne te répète pas)

- `_ensure_outcome_mapping` dans `qr_integration.py:15` : Partagé par `dialogue_manager_node.py` et `qr_reservation_bridge_node.py`.
- `extract_decoded_text` dans `qr_integration.py:78` : Utilisé à la fois par `QrScanGate.accept()` et `qr_reservation_bridge_node.on_qr_detection()`.
- `validate_backend_configuration` dans `qr_integration.py:52` : Utilisé par `qr_reservation_bridge_node` et `dialogue_manager_node`.
- `parse_destination_ids` dans `qr_integration.py:115` : Logique de parsing centralisée.

### Contre-exemples (où ça pourrait être amélioré) :

- `_navigation_driver.py` et `navigation_orchestrator.py` implémentent tous les deux `_cancel_late_goal()` (lignes 105 et 246) — c'est une duplication qui pourrait être extraite.
- Le pattern `_invalid()` est défini à la fois comme méthode d'instance (`DialogueManager._invalid:225`) et comme fonction standalone (`_invalid:234`) — ils font la même chose dans des portées différentes.

---

## 7. RÉSUMÉ — POINTS CLÉS POUR L'ORAL

1. **Maîtrisez le flux QR** : Caméra → qr_scanner_node → dialogue_manager → ValidateQr service → qr_reservation_bridge → POST HTTP vers backend → retour → déclenchement navigation → Nav2. C'est le fil rouge du projet.

2. **Justifiez l'hybride** : evo_navigation est hybride parce que les nœuds de sécurité (`cmd_vel_safety_gate`) nécessitent le C++ pour la latence, tandis que l'orchestration (`navigation_orchestrator.py`) bénéficie de Python pour la flexibilité.

3. **Expliquez la séparation machine d'état / adaptateur ROS** : `dialogue_manager.py` (0 dépendance ROS) + `dialogue_manager_node.py` (adaptateur ROS). C'est du pur SOLID — testable, maintenable, réutilisable.

4. **Défendez les choix de dépendances** : stdlib partout où c'est possible (`urllib` au lieu de `requests`, `http.server` au lieu de Flask). Le Jetson a des contraintes de déploiement.

5. **Montrez les patterns** : Tables de dispatch, Protocol pour les interfaces, jeton de requête pour les callbacks asynchrones, QrScanGate pour l'anti-doublon, DeadlineController pour les timeouts.
