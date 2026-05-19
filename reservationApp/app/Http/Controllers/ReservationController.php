<?php

namespace App\Http\Controllers;

use App\Models\Reservation;
use Illuminate\Http\Request;

class ReservationController extends Controller
{
    public function validateQRCode(Request $request) {
        $request->validate([
            'uuid' => 'required|uuid|exists:reservations,uuid',
        ]);

        $reservation = Reservation::where('uuid', $request->uuid)->first();

        if ($reservation->status !== 'pending') {
            return response()->json([
                'status' => 'error',
                'message' => "Cette réservation ne peut pas être validée (Statut actuel : {$reservation->status})."
            ], 422);
        }

        $reservation->update([
            'status' => 'validated',
            'validated_at' => now()
        ]);

        return response()->json([
            'status' => 'success',
            'message' => "La réservation a été validée avec succès.",
            'data' => $reservation
        ], 200);
    }
}

?>