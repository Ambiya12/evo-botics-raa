<?php

namespace Tests\Feature;

use Tests\TestCase;

class KioskModeTest extends TestCase
{
    public function test_kiosk_defaults_to_robot_camera_mode(): void
    {
        $this->get('/kiosk')
            ->assertOk()
            ->assertSee('Waiting for the robot camera', false);
    }

    public function test_kiosk_browser_scan_fallback_can_be_enabled(): void
    {
        $this->get('/kiosk?scan=browser')
            ->assertOk()
            ->assertSee('Browser camera fallback mode', false);
    }
}
