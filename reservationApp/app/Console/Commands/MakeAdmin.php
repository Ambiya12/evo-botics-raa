<?php

namespace App\Console\Commands;

use App\Enums\UserRole;
use App\Models\ActivityLog;
use App\Models\User;
use Illuminate\Console\Command;

class MakeAdmin extends Command
{
    protected $signature = 'app:make-admin {email}';

    protected $description = 'Promote an existing user to admin (and verify their email).';

    public function handle(): int
    {
        $email = $this->argument('email');
        $user = User::where('email', $email)->first();

        if (! $user) {
            $this->error("Aucun utilisateur trouvé pour l'email : {$email}");

            return self::FAILURE;
        }

        if ($user->isAdmin()) {
            $this->info("{$email} est déjà administrateur.");

            return self::SUCCESS;
        }

        $oldRole = $user->role;
        $user->role = UserRole::Admin;
        if (! $user->hasVerifiedEmail()) {
            $user->email_verified_at = now();
        }
        $user->save();

        ActivityLog::create([
            'action' => 'user.role_promoted',
            'description' => "Promotion admin via CLI pour {$user->email}",
            'loggable_id' => $user->id,
            'loggable_type' => User::class,
            'payload' => [
                'actor_id' => null,
                'actor_email' => 'console',
                'old_role' => $oldRole->value,
                'new_role' => UserRole::Admin->value,
            ],
        ]);

        $this->info("{$email} est maintenant administrateur.");

        return self::SUCCESS;
    }
}
