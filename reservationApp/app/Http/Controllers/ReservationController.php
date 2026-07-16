<?php

namespace App\Http\Controllers;

use App\Models\Reservation;
use App\Models\ActivityLog;
use App\Support\ReservationQrPayload;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Validation\ValidationException;

class ReservationController extends Controller
{
    public function validateQRCode(Request $request)
    {
        $request->validate([
            'uuid' => 'nullable|uuid|exists:reservations,uuid',
            'qr_payload' => 'nullable|string',
        ]);

        $uuid = $request->input('uuid');

        if (!$uuid && $request->filled('qr_payload')) {
            $decoded = json_decode($request->input('qr_payload'), true);
            if (!is_array($decoded) || !ReservationQrPayload::verify($decoded)) {
                throw ValidationException::withMessages([
                    'qr_payload' => ['The QR payload signature is invalid.'],
                ]);
            }
            $uuid = ReservationQrPayload::uuidFromQrPayload($request->input('qr_payload'));
        }

        if (!$uuid) {
            throw ValidationException::withMessages([
                'uuid' => ['A reservation UUID or signed QR payload is required.'],
            ]);
        }

        return DB::transaction(function () use ($request, $uuid) {
            $reservation = Reservation::with('bookingSession.room')
                ->where('uuid', $uuid)
                ->lockForUpdate()
                ->firstOrFail();

            if ($reservation->status !== 'pending') {
                $errorCode = $reservation->status === 'expired'
                    ? 'expired'
                    : 'already_used';

                ActivityLog::create([
                    'action' => 'validation_failed',
                    'description' => "Échec de validation : la réservation de {$reservation->customer_name} est en {$reservation->status}.",
                    'loggable_id' => $reservation->id,
                    'loggable_type' => Reservation::class,
                    'payload' => [
                        'attempted_at' => now(),
                        'current_status' => $reservation->status,
                        'ip' => $request->ip()
                    ]
                ]);

                return response()->json([
                    'status' => 'error',
                    'message' => "Cette réservation ne peut pas être validée (Statut actuel : {$reservation->status}).",
                    'error_code' => $errorCode,
                    'data' => $this->reservationPayload($reservation),
                ], 422);
            }

            $roomId = $reservation->bookingSession?->room_id;
            $navigableRoomIds = config('evo.navigable_room_ids', []);
            if (
                !is_int($roomId)
                || !in_array($roomId, $navigableRoomIds, true)
            ) {
                ActivityLog::create([
                    'action' => 'validation_failed',
                    'description' => 'Échec de validation : salle non prise en charge par le robot.',
                    'loggable_id' => $reservation->id,
                    'loggable_type' => Reservation::class,
                    'payload' => [
                        'attempted_at' => now(),
                        'room_id' => $roomId,
                        'reason' => 'unsupported_room',
                        'ip' => $request->ip(),
                    ],
                ]);

                return response()->json([
                    'status' => 'error',
                    'message' => "Cette salle n'est pas disponible pour le guidage robot.",
                    'error_code' => 'unsupported_room',
                    'data' => $this->reservationPayload($reservation),
                ], 422);
            }

            $reservation->update([
                'status' => 'validated',
                'validated_at' => now()
            ]);

            ActivityLog::create([
                'action' => 'reservation_validated',
                'description' => "Réservation validée pour {$reservation->customer_name}",
                'loggable_id' => $reservation->id,
                'loggable_type' => Reservation::class,
                'payload' => [
                    'validated_at' => $reservation->validated_at,
                    'uuid' => $reservation->uuid,
                    'method' => $request->filled('qr_payload') ? 'Signed QR Scan' : 'QR Scan'
                ]
            ]);

            return response()->json([
                'status' => 'success',
                'message' => "La réservation a été validée avec succès.",
                'data' => $this->reservationPayload($reservation->fresh()->load('bookingSession.room')),
            ], 200);
        });
    }

    public function myReservations()
    {
        return auth()->user()->reservations()->with('bookingSession.room')->get();
    }

    public function cancel($uuid)
    {
        $reservation = auth()->user()->reservations()->where('uuid', $uuid)->firstOrFail();
        
        return DB::transaction(function () use ($reservation) {
            $reservation->bookingSession->update(['is_available' => true]);

            $reservation->update(['status' => 'cancelled']);

            ActivityLog::create([
                'action' => 'reservation_cancelled',
                'description' => "Réservation annulée par l'utilisateur {$reservation->customer_name} pour la salle {$reservation->bookingSession->room->name}",
                'loggable_id' => $reservation->id,
                'loggable_type' => Reservation::class,
                'payload' => [
                    'user_id' => auth()->id(),
                    'customer_name' => $reservation->customer_name,
                    'uuid' => $reservation->uuid
                ]
            ]);

            return redirect()->back()->with(['message' => 'Réservation annulée avec succès.']);
        });
    }

    private function reservationPayload(Reservation $reservation): array
    {
        $session = $reservation->bookingSession;

        return [
            'uuid' => $reservation->uuid,
            'customer_name' => $reservation->customer_name,
            'customer_email' => $reservation->customer_email,
            'status' => $reservation->status,
            'room_id' => $session?->room_id,
            'room' => $session?->room?->name,
            'date' => optional($session?->date)->format('Y-m-d'),
            'start_at' => $session?->start_at,
            'end_at' => $session?->end_at,
        ];
    }
}
