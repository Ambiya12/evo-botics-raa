# 📅 Application de Réservation (reservationApp)

Cette application est développée avec **Laravel 12** (PHP) pour la partie Backend et **React** (via Inertia.js et Vite) pour la partie Frontend.

---

## 🛠️ Installation et Configuration Initiale

Commencez par cloner le dépôt puis ouvrez votre terminal et lancez ces commandes :

```bash
cd .\reservationApp\
composer install
```

```bash
./vendor/bin/sail composer require livewire/livewire
```

En attendant que tout s'installe, remplissez les champs DB_DATABASE, DB_USERNAME et DB_PASSWORD du fichier .env.example et renommez le .env.

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
./vendor/bin/sail npm run dev
```

---

## 👤 Rôles et administration

L'application gère **deux rôles** : `user` (par défaut) et `admin`. Toute route sous le préfixe
`admin/` (dashboard robot, gestion des utilisateurs) est réservée aux administrateurs ; les
vérifications sont faites côté backend. À l'inscription, un compte est **toujours** créé avec le
rôle `user` — il est impossible de choisir son rôle.

### Promouvoir un utilisateur en administrateur (commande)

La promotion passe par la commande artisan `app:make-admin`, qui prend l'**e-mail d'un compte
existant**. Elle promeut le compte, **vérifie automatiquement son e-mail** (sinon le middleware
`verified` bloquerait le nouvel admin) et journalise l'opération dans `activity_logs`.

```bash
# En local (PHP direct)
php artisan app:make-admin email@exemple.com

# Avec Docker / Sail
./vendor/bin/sail artisan app:make-admin email@exemple.com
```

Comportement :

- ❌ E-mail inconnu → la commande échoue (code de sortie 1), aucun changement.
- ✅ Compte déjà admin → message neutre, aucune action (commande idempotente).
- ✅ Sinon → le compte devient `admin`, e-mail vérifié, trace ajoutée à l'audit.

### Créer le tout premier administrateur

Sur une base fraîche, il n'existe encore aucun admin. La procédure est :

1. Créer un compte normalement via la page d'inscription (`/register`).
2. Le promouvoir avec la commande ci-dessus :
    ```bash
    php artisan app:make-admin votre-email@exemple.com
    ```
3. Se connecter : l'accès aux routes `admin/*` est désormais ouvert.

> En environnement de **développement**, le seeder crée déjà un admin prêt à l'emploi :
> `admin@example.com` / mot de passe `password` (via `php artisan migrate:fresh --seed`).

### Promouvoir / rétrograder ensuite

Une fois connecté en admin, la page **`/admin/users`** permet de promouvoir ou rétrograder les
autres comptes (avec confirmation). Garde-fous :

- impossible de modifier **son propre** rôle ;
- impossible de rétrograder le **dernier** administrateur.

### Dépannage (dernier recours)

Si aucun admin n'est plus accessible et que la commande ne peut pas être utilisée, on peut, en
**bris de glace uniquement**, forcer le rôle via tinker :

```bash
php artisan tinker
>>> $u = \App\Models\User::firstWhere('email', 'votre-email@exemple.com');
>>> $u->update(['role' => 'admin']);
>>> $u->markEmailAsVerified();
```

⚠️ Ce chemin **n'est pas tracé** dans `activity_logs` et contourne les garde-fous : à n'utiliser
qu'en cas d'urgence. Privilégier toujours `app:make-admin`.
