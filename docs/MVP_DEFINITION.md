# MVP Definition — Evo-Botics (Business Center Reception)

## 1) Problem + User (3 lines)
Business centers need fast, reliable visitor reception without overloading front-desk staff.
Visitors should complete check-in through a simple contactless flow, without manual input.
The MVP targets first-time and time-constrained visitors who need a smooth voice-first flow: validate reservation, receive badge, be guided, then robot returns to reception point.

## 2) MVP Scope (max 5 bullets)
- Start a voice-first welcome and reservation validation flow, with screen used only for status feedback.
- Validate reservation through QR code only via the real API and fail closed when it is unavailable.
- Distribute the visitor badge after successful reservation validation.
- Guide the visitor to the correct room waypoint on the same floor with safe autonomous navigation.
- Return autonomously to the original reception/standby position after drop-off, and notify staff only on exceptions.

## 3) 3 Measurable Success Criteria
1. **Reservation latency:** median QR validation time ≤ 3.0 seconds over at least 100 scans in indoor test conditions.
2. **Flow completion:** ≥ 90% of scripted sessions complete end-to-end (welcome → validate → badge distribution → guidance → return to reception point) without manual operator intervention.
3. **Operational safety/reliability:** 0 collisions in acceptance runs and emergency stop reaction ≤ 1 second in 100% of tested trigger events.

## 4) Constraints
- **Autonomy:** one-floor indoor navigation only; no stairs/elevators; no outdoor operation.
- **Latency:** user-visible responses must remain fluid; reservation validation target ≤ 3 seconds median.
- **Budget/Resources:** single ROSMASTER M3 Pro + Jetson Orin NX platform, limited hardware availability, team of 4 developers.
- **Interaction UX:** visitors do not interact manually with the screen; the screen is feedback-only (e.g., reservation valid/invalid).
- **Environment:** flat indoor surfaces, dynamic human obstacles, variable noise levels affecting speech recognition.
- **Delivery:** MVP must be deliverable within the module timeline and prioritized around P0 scope only.

## 5) Top 3 Risks + Plan B (one sentence each)
- **Risk:** Speech recognition quality degrades in noisy areas; **Plan B:** switch to simple voice confirmations plus clear on-screen status messages before executing critical actions.
- **Risk:** Badge distribution mechanism jams or fails; **Plan B:** trigger staff alert and switch to manual badge handover while keeping guidance available.
- **Risk:** Navigation blocks or drifts in crowded corridors (including return path); **Plan B:** trigger safe stop, notify staff immediately, and hand over to assisted/manual guidance mode.

---

# Définition du MVP — Evo-Botics (Accueil en centre d'affaires)

## 1) Problème + utilisateur (3 lignes)
Les centres d'affaires ont besoin d'un accueil visiteur rapide et fiable sans surcharger le personnel d'accueil.
Les visiteurs doivent finaliser le check-in via un parcours simple et sans contact, sans saisie manuelle.
Le MVP cible les primo-visiteurs et les profils pressés avec un flux vocal fluide : valider la réservation, recevoir un badge, être guidé, puis retour du robot au point d'accueil.

## 2) Périmètre MVP (5 bullets max)
- Démarrer un accueil vocal et un flux de validation de réservation, avec écran utilisé uniquement pour le retour d'état.
- Valider la réservation uniquement via QR code par l'API réelle et bloquer le flux si elle est indisponible.
- Distribuer le badge visiteur après validation réussie de la réservation.
- Guider le visiteur vers le waypoint de la salle sur le même étage avec une navigation autonome sécurisée.
- Revenir de manière autonome à la position d'accueil/veille après le dépôt, et notifier le personnel uniquement en cas d'exception.

## 3) 3 critères de succès mesurables
1. **Latence de réservation :** temps médian de validation QR ≤ 3,0 secondes sur au moins 100 scans en conditions indoor.
2. **Complétion du flux :** ≥ 90 % des sessions scriptées se terminent de bout en bout (accueil → validation → distribution badge → guidage → retour point d'accueil) sans intervention opérateur.
3. **Sécurité/fiabilité opérationnelle :** 0 collision pendant les runs d'acceptation et réaction de l'arrêt d'urgence ≤ 1 seconde dans 100 % des déclenchements testés.

## 4) Contraintes
- **Autonomie :** navigation intérieure sur un seul étage ; pas d'escaliers/ascenseurs ; pas d'usage extérieur.
- **Latence :** les réponses visibles utilisateur doivent rester fluides ; cible de validation réservation ≤ 3 secondes en médiane.
- **Budget/Ressources :** une seule plateforme ROSMASTER M3 Pro + Jetson Orin NX, disponibilité matérielle limitée, équipe de 4 développeurs.
- **UX d'interaction :** les visiteurs n'interagissent pas manuellement avec l'écran ; l'écran sert uniquement au feedback (ex. réservation valide/invalide).
- **Environnement :** sols intérieurs plats, obstacles humains dynamiques, bruit ambiant variable impactant la reconnaissance vocale.
- **Livraison :** le MVP doit être livrable dans le délai du module et rester centré sur le périmètre P0.

## 5) Top 3 risques + plan B (une phrase chacun)
- **Risque :** la reconnaissance vocale se dégrade en environnement bruyant ; **Plan B :** basculer sur des confirmations vocales simples avec messages d'état clairs à l'écran avant toute action critique.
- **Risque :** le mécanisme de distribution de badge se bloque ou échoue ; **Plan B :** déclencher une alerte staff et passer en remise manuelle du badge tout en conservant le guidage.
- **Risque :** la navigation se bloque ou dérive dans les couloirs chargés (y compris au retour) ; **Plan B :** déclencher un arrêt sécurisé, notifier immédiatement le personnel, puis basculer en assistance/contrôle manuel.
