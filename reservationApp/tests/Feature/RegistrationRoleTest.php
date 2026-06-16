<?php

namespace Tests\Feature;

use App\Enums\UserRole;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class RegistrationRoleTest extends TestCase
{
    use RefreshDatabase;

    public function test_web_register_ignores_role_payload(): void
    {
        $this->post('/register', [
            'name' => 'Web User',
            'email' => 'web@example.com',
            'password' => 'password',
            'password_confirmation' => 'password',
            'role' => 'admin',
        ]);

        $user = User::where('email', 'web@example.com')->firstOrFail();
        $this->assertSame(UserRole::User, $user->role);
    }

    public function test_api_register_ignores_role_payload(): void
    {
        $this->postJson('/api/register', [
            'name' => 'Api User',
            'email' => 'api@example.com',
            'password' => 'password',
            'password_confirmation' => 'password',
            'role' => 'admin',
        ])->assertStatus(201);

        $user = User::where('email', 'api@example.com')->firstOrFail();
        $this->assertSame(UserRole::User, $user->role);
    }
}
