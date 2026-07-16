<?php

namespace Tests\Feature;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Inertia\Testing\AssertableInertia as Assert;
use Tests\TestCase;

class InertiaSharedRoleTest extends TestCase
{
    use RefreshDatabase;

    public function test_shared_auth_user_exposes_role(): void
    {
        $admin = User::factory()->admin()->create();

        $this->actingAs($admin)
            ->get('/admin/users')
            ->assertInertia(fn (Assert $page) => $page
                ->where('auth.user.role', 'admin')
                ->has('users')
            );
    }

    public function test_users_index_lists_users_for_admin(): void
    {
        $admin = User::factory()->admin()->create();
        User::factory()->count(2)->create();

        $this->actingAs($admin)
            ->get('/admin/users')
            ->assertInertia(fn (Assert $page) => $page
                ->component('Admin/Users/Index')
                ->has('users', 3)
            );
    }

    public function test_non_admin_cannot_list_users(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/admin/users')->assertStatus(403);
    }
}
