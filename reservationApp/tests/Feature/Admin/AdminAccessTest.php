<?php

namespace Tests\Feature\Admin;

use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Route;
use Tests\TestCase;

class AdminAccessTest extends TestCase
{
    use RefreshDatabase;

    public function test_guest_is_redirected_to_login(): void
    {
        $this->get('/admin/robot')->assertRedirect('/login');
    }

    public function test_non_admin_gets_403_on_admin_routes(): void
    {
        $user = User::factory()->create();

        $this->actingAs($user)->get('/admin/robot')->assertStatus(403);
    }

    public function test_admin_can_access_admin_robot(): void
    {
        $admin = User::factory()->admin()->create();

        $this->actingAs($admin)->get('/admin/robot')->assertStatus(200);
    }

    public function test_admin_alias_is_registered_without_runtime_error(): void
    {
        Route::middleware('admin')->get('/_smoke_admin', fn () => 'ok');
        $admin = User::factory()->admin()->create();

        $this->actingAs($admin)->get('/_smoke_admin')->assertOk();
    }
}
