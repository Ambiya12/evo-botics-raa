<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\Session;
use App\Models\Reservation;
use Illuminate\Support\Facades\DB;

class SessionController extends Controller
{
    public function bookSession(Request $request) {
        $request->validate([
            'date' => 'required|date|after_or_equal:today',
            'start_at' => 'required',
            'end_at' => 'required|after:start_at',
            'attendee_count' => 'required|integer|min:1',
            'customer_name' => 'required|string',
            'customer_email' => 'required|email',
        ]);

        $sessionsAvailables = Session::where('date', $request->date)
            ->where('start_at', $request->start_at)
            ->where('end_at', $request->end_at)
            ->where('is_available', true)
            ->get();

        if ($sessionsAvailables->isEmpty()) {
            return response()->json([
                'status' => 'error',
                'message' => "Aucune session disponible pour ce créneau horaire."
            ], 404);
        }

        $session = $sessionsAvailables->first(function ($session) use ($request) {
            return $session->room->capacity >= $request->attendee_count;
        });

        if (!$session) {
            return response()->json([
                'status' => 'error',
                'message' => "Aucune session disponible avec une capacité suffisante pour {$request->attendee_count} personnes."
            ], 404);
        }

        return DB::transaction(function () use ($session, $request) {
            return $this->createReservation($session, $request);
        });
    }

    private function createReservation(Session $session, Request $request) {
        $reservation = Reservation::create([
            'customer_name' => $request->customer_name,
            'customer_email' => $request->customer_email,
            'reservation_date' => $request->date . ' ' . $request->start_at,
            'status' => 'pending',
            'session_id' => $session->id,
            'attendee_count' => $request->attendee_count,
        ]);

        $session->update(['is_available' => false]);

        return response()->json([
            'status' => 'success',
            'message' => "La session a été réservée avec succès. Vous recevrez un mail de confirmation sous peu.",
            'data' => [
                'reservation' => $reservation,
                'session' => $session
            ]
        ], 201);
    }
}
