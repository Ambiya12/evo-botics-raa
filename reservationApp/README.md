# 📅 Application de Réservation (reservationApp)

Cette application est développée avec **Laravel 12** (PHP) pour la partie Backend et **React** (via Inertia.js et Vite) pour la partie Frontend.

---

## 🛠️ Installation et Configuration Initiale

Commencez par cloner le dépôt puis remplissez les champs DB_DATABASE, DB_USERNAME et DB_PASSWORD du fichier .env.example.

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
npm run dev
```