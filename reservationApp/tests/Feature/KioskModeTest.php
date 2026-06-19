<?php

namespace Tests\Feature;

use App\Livewire\KioskManager;
use Livewire\Livewire;
use Tests\TestCase;

class KioskModeTest extends TestCase
{
    public function test_kiosk_defaults_to_robot_camera_mode(): void
    {
        $this->get('/kiosk')
            ->assertOk()
            ->assertSee('Waiting for the robot camera', false)
            ->assertDontSee('throttle_rate', false);
    }

    public function test_kiosk_browser_scan_fallback_can_be_enabled(): void
    {
        $this->get('/kiosk?scan=browser')
            ->assertOk()
            ->assertSee('Browser camera fallback mode', false);
    }

    public function test_robot_success_status_moves_kiosk_to_success_result(): void
    {
        Livewire::test(KioskManager::class)
            ->call('applyRobotQrStatus', [
                'state' => 'success',
                'message' => 'Reservation validated.',
                'reservation' => [
                    'uuid' => 'reservation-uuid',
                    'customer_name' => 'Ada Lovelace',
                    'room' => 'Demo Room',
                    'date' => '2026-06-19',
                    'start_at' => '10:00',
                    'end_at' => '11:00',
                ],
            ])
            ->assertSet('step', 'result')
            ->assertSet('resultStatus', 'success')
            ->assertSet('reservation.name', 'Ada Lovelace')
            ->assertSet('reservation.room', 'Demo Room')
            ->assertSee('Your reservation has been validated.');
    }

    public function test_robot_error_status_moves_kiosk_to_error_result(): void
    {
        Livewire::test(KioskManager::class)
            ->call('applyRobotQrStatus', [
                'state' => 'error',
                'message' => 'This reservation has already been used.',
                'error_code' => 'already_used',
            ])
            ->assertSet('step', 'result')
            ->assertSet('resultStatus', 'error')
            ->assertSet('robotErrorCode', 'already_used')
            ->assertSee('This reservation has already been used.');
    }
}
