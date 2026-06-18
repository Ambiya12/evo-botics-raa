<?php

namespace App\Support;

use App\Models\Reservation;
use SimpleSoftwareIO\QrCode\Facades\QrCode;

class ReservationQrPayload
{
    public static function forReservation(Reservation $reservation): array
    {
        $reservation->loadMissing('bookingSession.room');

        return [
            'type' => 'reservation',
            'version' => 1,
            'uuid' => $reservation->uuid,
            'customer' => [
                'name' => $reservation->customer_name,
                'email' => $reservation->customer_email,
            ],
            'reservation' => [
                'date' => optional($reservation->bookingSession?->date)->format('Y-m-d'),
                'startTime' => $reservation->bookingSession?->start_at,
                'endTime' => $reservation->bookingSession?->end_at,
                'attendeeCount' => $reservation->attendee_count,
                'room' => $reservation->bookingSession?->room?->name,
            ],
        ];
    }

    public static function forLegacyReservation(
        string $name,
        string $email,
        string $date,
        string $startTime,
        string $endTime,
        int $people,
        ?string $uuid = null
    ): array {
        return [
            'type' => 'reservation',
            'version' => 1,
            'uuid' => $uuid,
            'customer' => [
                'name' => $name,
                'email' => $email,
            ],
            'reservation' => [
                'date' => $date,
                'startTime' => $startTime,
                'endTime' => $endTime,
                'attendeeCount' => $people,
                'room' => null,
            ],
        ];
    }

    public static function encode(array $payload): string
    {
        $signed = $payload;
        $signed['signature'] = self::signature($payload);

        return self::canonicalJson($signed);
    }

    public static function dataUri(array $payload, int $size = 300): string
    {
        $svg = QrCode::size($size)->generate(self::encode($payload));

        return 'data:image/svg+xml;base64,' . base64_encode($svg);
    }

    public static function verify(array $signedPayload): bool
    {
        $signature = $signedPayload['signature'] ?? null;
        if (!is_string($signature) || $signature === '') {
            return false;
        }

        unset($signedPayload['signature']);

        return hash_equals(self::signature($signedPayload), $signature);
    }

    public static function uuidFromQrPayload(string $qrPayload): ?string
    {
        $decoded = json_decode($qrPayload, true);
        if (!is_array($decoded)) {
            return null;
        }

        if (isset($decoded['uuid']) && is_string($decoded['uuid'])) {
            return $decoded['uuid'];
        }

        // Backward compatibility for the previous payload/signature envelope.
        if (isset($decoded['payload']) && is_string($decoded['payload'])) {
            $legacyPayload = json_decode($decoded['payload'], true);
            if (is_array($legacyPayload) && isset($legacyPayload['uuid']) && is_string($legacyPayload['uuid'])) {
                return $legacyPayload['uuid'];
            }
        }

        return null;
    }

    private static function signature(array $payload): string
    {
        return hash_hmac('sha256', self::canonicalJson($payload), config('app.key'));
    }

    private static function canonicalJson(array $payload): string
    {
        return json_encode($payload, JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE);
    }
}
