<?php

namespace Tests\Feature;

use App\Models\Reservation;
use App\Support\ReservationQrPayload;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Tests\TestCase;

class ReservationQrValidationTest extends TestCase
{
    use RefreshDatabase;

    public function test_signed_qr_payload_validates_pending_reservation(): void
    {
        $reservation = Reservation::factory()->create(['status' => 'pending']);
        $reservation->load('bookingSession.room');
        $qrPayload = ReservationQrPayload::encode(
            ReservationQrPayload::forReservation($reservation)
        );

        $response = $this->postJson('/api/reservations/validate', [
            'qr_payload' => $qrPayload,
        ]);

        $response
            ->assertOk()
            ->assertJsonPath('status', 'success')
            ->assertJsonPath('data.uuid', $reservation->uuid)
            ->assertJsonPath('data.customer_name', $reservation->customer_name)
            ->assertJsonPath('data.room', $reservation->bookingSession->room->name)
            ->assertJsonPath('data.date', $reservation->bookingSession->date->format('Y-m-d'))
            ->assertJsonPath('data.start_at', $reservation->bookingSession->start_at)
            ->assertJsonPath('data.end_at', $reservation->bookingSession->end_at);

        $this->assertDatabaseHas('reservations', [
            'id' => $reservation->id,
            'status' => 'validated',
        ]);

        $this->assertDatabaseHas('activity_logs', [
            'action' => 'reservation_validated',
            'loggable_id' => $reservation->id,
        ]);
    }

    public function test_tampered_qr_payload_is_rejected(): void
    {
        $reservation = Reservation::factory()->create(['status' => 'pending']);
        $payload = ReservationQrPayload::forReservation($reservation);
        $payload['customer']['name'] = 'Tampered Name';

        $response = $this->postJson('/api/reservations/validate', [
            'qr_payload' => json_encode(
                array_merge($payload, ['signature' => 'invalid']),
                JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE
            ),
        ]);

        $response
            ->assertUnprocessable()
            ->assertJsonValidationErrors('qr_payload');

        $this->assertDatabaseHas('reservations', [
            'id' => $reservation->id,
            'status' => 'pending',
        ]);
    }

    public function test_already_validated_reservation_returns_error_state(): void
    {
        $reservation = Reservation::factory()->create(['status' => 'validated']);
        $qrPayload = ReservationQrPayload::encode(
            ReservationQrPayload::forReservation($reservation)
        );

        $response = $this->postJson('/api/reservations/validate', [
            'qr_payload' => $qrPayload,
        ]);

        $response
            ->assertUnprocessable()
            ->assertJsonPath('status', 'error')
            ->assertJsonPath('error_code', 'already_used')
            ->assertJsonPath('data.uuid', $reservation->uuid);
    }
}
