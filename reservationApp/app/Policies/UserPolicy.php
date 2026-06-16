<?php

namespace App\Policies;

use App\Models\User;

class UserPolicy
{
    public function viewAny(User $actor): bool
    {
        return $actor->isAdmin();
    }

    public function updateRole(User $actor, User $target): bool
    {
        // Admin only, and never your own role (anchors the no-self-modification rule).
        return $actor->isAdmin() && $actor->id !== $target->id;
    }
}
