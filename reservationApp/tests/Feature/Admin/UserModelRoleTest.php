<?php

namespace Tests\Feature\Admin;

use App\Enums\UserRole;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class UserModelRoleTest extends TestCase
{
    use RefreshDatabase;

    public function test_new_user_defaults_to_user_role(): void
    {
        $user = User::factory()->create();

        $this->assertSame(UserRole::User, $user->fresh()->role);
        $this->assertFalse($user->isAdmin());
    }

    public function test_admin_factory_state_sets_admin_role(): void
    {
        $admin = User::factory()->admin()->create();

        $this->assertSame(UserRole::Admin, $admin->fresh()->role);
        $this->assertTrue($admin->isAdmin());
    }

    public function test_role_is_guarded_against_mass_assignment(): void
    {
        // Stays 'user' thanks to both legs of the guard: `role` is absent from
        // $fillable (so create() ignores it) and the migration default is 'user'.
        $user = User::create([
            'name' => 'Mallory',
            'email' => 'mallory@example.com',
            'password' => 'password',
            'role' => 'admin',
        ]);

        $this->assertSame(UserRole::User, $user->fresh()->role);
    }
}
