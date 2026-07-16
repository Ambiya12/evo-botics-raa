<?php

namespace Tests\Feature\Admin;

use App\Enums\UserRole;
use App\Models\ActivityLog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class UserRoleManagementTest extends TestCase
{
    use RefreshDatabase;

    public function test_admin_promotes_user_and_logs_it(): void
    {
        $admin = User::factory()->admin()->create();
        $target = User::factory()->create();

        $this->actingAs($admin)
            ->patch("/admin/users/{$target->id}/role", ['role' => 'admin'])
            ->assertRedirect();

        $this->assertSame(UserRole::Admin, $target->fresh()->role);
        $this->assertSame(1, ActivityLog::where('action', 'user.role_promoted')->count());
    }

    public function test_admin_demotes_user_and_logs_it(): void
    {
        $admin = User::factory()->admin()->create();
        $target = User::factory()->admin()->create();

        $this->actingAs($admin)
            ->patch("/admin/users/{$target->id}/role", ['role' => 'user'])
            ->assertRedirect();

        $this->assertSame(UserRole::User, $target->fresh()->role);
        $this->assertSame(1, ActivityLog::where('action', 'user.role_demoted')->count());
    }

    public function test_invalid_role_is_rejected(): void
    {
        $admin = User::factory()->admin()->create();
        $target = User::factory()->create();

        $this->actingAs($admin)
            ->patch("/admin/users/{$target->id}/role", ['role' => 'superadmin'])
            ->assertSessionHasErrors('role');

        $this->assertSame(UserRole::User, $target->fresh()->role);
    }

    public function test_admin_cannot_change_own_role(): void
    {
        $admin = User::factory()->admin()->create();

        $this->actingAs($admin)
            ->patch("/admin/users/{$admin->id}/role", ['role' => 'user'])
            ->assertStatus(403);

        $this->assertSame(UserRole::Admin, $admin->fresh()->role);
    }

    public function test_invariant_never_drops_below_one_admin(): void
    {
        $a = User::factory()->admin()->create();
        $b = User::factory()->admin()->create();

        // Demote b (allowed, two admins) -> one admin remains.
        $this->actingAs($a)->patch("/admin/users/{$b->id}/role", ['role' => 'user'])->assertRedirect();
        $this->assertSame(1, User::where('role', 'admin')->count());

        // a cannot demote itself (self-rule) -> 403, still one admin.
        $this->actingAs($a)->patch("/admin/users/{$a->id}/role", ['role' => 'user'])->assertStatus(403);
        $this->assertSame(1, User::where('role', 'admin')->count());
    }

    public function test_non_admin_cannot_update_a_role(): void
    {
        $user = User::factory()->create();
        $target = User::factory()->create();

        $this->actingAs($user)
            ->patch("/admin/users/{$target->id}/role", ['role' => 'admin'])
            ->assertStatus(403);

        $this->assertSame(UserRole::User, $target->fresh()->role);
    }

    public function test_no_op_role_change_writes_no_log_and_no_success_flash(): void
    {
        $admin = User::factory()->admin()->create();
        $target = User::factory()->admin()->create();

        $this->actingAs($admin)
            ->patch("/admin/users/{$target->id}/role", ['role' => 'admin'])
            ->assertRedirect()
            ->assertSessionMissing('success');

        $this->assertSame(0, ActivityLog::count());
        $this->assertSame(UserRole::Admin, $target->fresh()->role);
    }
}
