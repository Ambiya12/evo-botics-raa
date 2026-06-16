<?php

namespace Tests\Unit;

use App\Enums\UserRole;
use Tests\TestCase;

class UserRoleTest extends TestCase
{
    public function test_values_returns_all_backing_strings(): void
    {
        $this->assertSame(['user', 'admin'], UserRole::values());
    }

    public function test_cases_have_expected_values(): void
    {
        $this->assertSame('user', UserRole::User->value);
        $this->assertSame('admin', UserRole::Admin->value);
    }
}
