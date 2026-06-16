<?php

namespace App\Http\Controllers\Admin;

use App\Enums\UserRole;
use App\Http\Controllers\Controller;
use App\Models\ActivityLog;
use App\Models\User;
use Illuminate\Http\RedirectResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\Rule;
use Inertia\Inertia;
use Inertia\Response;

class UserManagementController extends Controller
{
    public function index(Request $request): Response
    {
        $this->authorize('viewAny', User::class);

        $adminCount = User::where('role', UserRole::Admin->value)->count();
        $authId = $request->user()->id;

        $users = User::orderBy('name')
            ->get(['id', 'name', 'email', 'role'])
            ->map(fn (User $user) => [
                'id' => $user->id,
                'name' => $user->name,
                'email' => $user->email,
                'role' => $user->role->value,
                'isSelf' => $user->id === $authId,
                'isLastAdmin' => $user->role === UserRole::Admin && $adminCount <= 1,
            ]);

        return Inertia::render('Admin/Users/Index', ['users' => $users]);
    }

    public function updateRole(Request $request, User $user): RedirectResponse
    {
        $this->authorize('updateRole', $user);

        $validated = $request->validate([
            'role' => ['required', Rule::in(UserRole::values())],
        ]);

        $newRole = UserRole::from($validated['role']);

        DB::transaction(function () use ($request, $user, $newRole) {
            $oldRole = $user->role;

            if ($oldRole === UserRole::Admin && $newRole === UserRole::User) {
                $adminCount = User::where('role', UserRole::Admin->value)
                    ->lockForUpdate()
                    ->count();

                if ($adminCount <= 1) {
                    abort(422, 'Impossible de rétrograder le dernier administrateur.');
                }
            }

            if ($oldRole === $newRole) {
                return; // no-op, no log
            }

            $user->role = $newRole;
            $user->save();

            ActivityLog::create([
                'action' => $newRole === UserRole::Admin ? 'user.role_promoted' : 'user.role_demoted',
                'description' => "Changement de rôle de {$user->email} : {$oldRole->value} -> {$newRole->value}",
                'loggable_id' => $user->id,
                'loggable_type' => User::class,
                'payload' => [
                    'actor_id' => $request->user()->id,
                    'actor_email' => $request->user()->email,
                    'old_role' => $oldRole->value,
                    'new_role' => $newRole->value,
                ],
            ]);
        });

        $label = $newRole === UserRole::Admin ? 'promu administrateur' : 'rétrogradé en utilisateur';

        return back()->with('success', "{$user->name} a été {$label}.");
    }
}
