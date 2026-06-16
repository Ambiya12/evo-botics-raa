<?php

namespace Tests\Feature\Admin;

use App\Enums\UserRole;
use App\Models\ActivityLog;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class MakeAdminCommandTest extends TestCase
{
    use RefreshDatabase;

    public function test_promotes_existing_user_and_verifies_email(): void
    {
        $user = User::factory()->unverified()->create(['email' => 'boot@example.com']);

        $this->artisan('app:make-admin', ['email' => 'boot@example.com'])
            ->assertExitCode(0);

        $user->refresh();
        $this->assertSame(UserRole::Admin, $user->role);
        $this->assertNotNull($user->email_verified_at);
        $this->assertSame(1, ActivityLog::where('action', 'user.role_promoted')->count());
    }

    public function test_fails_when_email_unknown(): void
    {
        $this->artisan('app:make-admin', ['email' => 'nobody@example.com'])
            ->assertExitCode(1);

        $this->assertSame(0, ActivityLog::count());
    }

    public function test_is_idempotent_for_existing_admin(): void
    {
        User::factory()->admin()->create(['email' => 'already@example.com']);

        $this->artisan('app:make-admin', ['email' => 'already@example.com'])
            ->assertExitCode(0);

        $this->assertSame(0, ActivityLog::where('action', 'user.role_promoted')->count());
    }
}
