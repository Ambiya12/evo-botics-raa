<?php

namespace Tests\Feature;

use App\Livewire\Reservation;
use App\Mail\ReservationConfirmed;
use App\Models\BookingSession;
use App\Models\Room;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Mail;
use Livewire\Livewire;
use Tests\TestCase;

class ReservationPageBookingTest extends TestCase
{
    use RefreshDatabase;

    public function test_reservation_page_creates_real_pending_reservation_and_displays_qr(): void
    {
        Mail::fake();

        $user = User::factory()->create();
        $room = Room::factory()->create([
            'name' => 'Demo Room',
            'max_capacity' => 12,
        ]);
        $session = BookingSession::factory()->create([
            'room_id' => $room->id,
            'date' => now()->addDay()->format('Y-m-d'),
            'start_at' => '10:00',
            'end_at' => '11:00',
            'is_available' => true,
        ]);

        $this->actingAs($user);

        Livewire::test(Reservation::class)
            ->set('name', 'Ada Lovelace')
            ->set('email', 'ada@example.com')
            ->set('selectedDate', $session->date->format('Y-m-d'))
            ->set('selectedStartTime', '10:00')
            ->set('selectedEndTime', '11:00')
            ->set('peopleCount', 4)
            ->call('reserve')
            ->assertSet('step', 'checking')
            ->call('checkAvailability')
            ->assertSet('step', 'result')
            ->assertSet('roomFound', true)
            ->assertSet('reservedRoomName', 'Demo Room')
            ->assertSee('Reservation QR Code');

        $this->assertDatabaseHas('reservations', [
            'customer_name' => 'Ada Lovelace',
            'customer_email' => 'ada@example.com',
            'status' => 'pending',
            'attendee_count' => 4,
            'booking_session_id' => $session->id,
        ]);

        $this->assertDatabaseHas('booking_sessions', [
            'id' => $session->id,
            'is_available' => false,
        ]);

        Mail::assertSent(ReservationConfirmed::class);
    }

    public function test_reservation_page_reports_no_room_without_creating_reservation(): void
    {
        Mail::fake();

        $user = User::factory()->create();
        $room = Room::factory()->create(['max_capacity' => 2]);
        $session = BookingSession::factory()->create([
            'room_id' => $room->id,
            'date' => now()->addDay()->format('Y-m-d'),
            'start_at' => '10:00',
            'end_at' => '11:00',
            'is_available' => true,
        ]);

        $this->actingAs($user);

        Livewire::test(Reservation::class)
            ->set('name', 'Grace Hopper')
            ->set('email', 'grace@example.com')
            ->set('selectedDate', $session->date->format('Y-m-d'))
            ->set('selectedStartTime', '10:00')
            ->set('selectedEndTime', '11:00')
            ->set('peopleCount', 4)
            ->call('reserve')
            ->call('checkAvailability')
            ->assertSet('step', 'result')
            ->assertSet('roomFound', false)
            ->assertSet('qrCodeDataUri', '');

        $this->assertDatabaseMissing('reservations', [
            'customer_email' => 'grace@example.com',
        ]);

        Mail::assertNothingSent();
    }
}
