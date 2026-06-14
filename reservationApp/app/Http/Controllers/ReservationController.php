<?php

namespace App\Http\Controllers;

use App\Models\Reservation;
use App\Models\ActivityLog;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;

class ReservationController extends Controller
{
    public function validateQRCode(Request $request)
    {
        $request->validate([
            'uuid' => 'required|uuid|exists:reservations,uuid',
        ]);

        $reservation = Reservation::where('uuid', $request->uuid)->first();

        if ($reservation->status !== 'pending') {
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
                'message' => "Cette réservation ne peut pas être validée (Statut actuel : {$reservation->status})."
            ], 422);
        }

        $reservation->update([
            'status' => 'validated',
            'validated_at' => now()
        ]);

        ActivityLog::create([
            'action' => 'reservation_validated',
            'description' => "Réservation validée pour {$request->customer_name}",
            'loggable_id' => $reservation->id,
            'loggable_type' => Reservation::class,
            'payload' => [
                'validated_at' => $reservation->validated_at,
                'uuid' => $reservation->uuid,
                'method' => "QR Scan"
            ]
        ]);

        return response()->json([
            'status' => 'success',
            'message' => "La réservation a été validée avec succès.",
            'data' => $reservation
        ], 200);
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

            ActivityLog::create([
                'event_type' => 'reservation_cancelled',
                'description' => "Réservation annulée par l'utilisateur pour la salle {$reservation->bookingSession->room->name}",
                'payload' => [
                    'user_id' => auth()->id(),
                    'customer_name' => $reservation->customer_name,
                    'uuid' => $reservation->uuid
                ]
            ]);
            
            $reservation->delete();

            return response()->json(['message' => 'Réservation annulée avec succès.']);
        });
    }
}

?>