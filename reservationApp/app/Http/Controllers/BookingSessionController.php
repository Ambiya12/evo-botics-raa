<?php

namespace App\Http\Controllers;

use Illuminate\Http\Request;
use App\Models\BookingSession;
use App\Models\Reservation;
use App\Models\ActivityLog;
use Illuminate\Support\Facades\DB;

class BookingSessionController extends Controller
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

        $sessionsAvailables = BookingSession::where('date', $request->date)
            ->where('start_at', $request->start_at)
            ->where('end_at', $request->end_at)
            ->where('is_available', true)
            ->get();

        if ($sessionsAvailables->isEmpty()) {
            ActivityLog::create([
                'action' => 'booking_failed_no_slot',
                'description' => "Échec : Aucun créneau libre le {$request->date} à {$request->start_at}",
                'payload' => $request->all()
            ]);

            return response()->json([
                'status' => 'error',
                'message' => "Aucune salle disponible pour ce créneau horaire."
            ], 404);
        }

        $session = $sessionsAvailables->first(function ($session) use ($request) {
            return $session->room->max_capacity >= $request->attendee_count;
        });

        if (!$session) {
            ActivityLog::create([
                'action' => 'booking_failed_capacity',
                'description' => "Échec : Salles complètes pour {$request->attendee_count} personnes le {$request->date}",
                'payload' => $request->all()
            ]);

            return response()->json([
                'status' => 'error',
                'message' => "Aucune salle disponible avec une capacité suffisante pour {$request->attendee_count} personnes."
            ], 404);
        }

        return DB::transaction(function () use ($session, $request) {
            return $this->createReservation($session, $request);
        });
    }

    private function createReservation(BookingSession $session, Request $request) {
        $reservation = Reservation::create([
            'customer_name' => $request->customer_name,
            'customer_email' => $request->customer_email,
            'reservation_date' => $request->date . ' ' . $request->start_at,
            'status' => 'pending',
            'session_id' => $session->id,
            'attendee_count' => $request->attendee_count,
        ]);

        $session->update(['is_available' => false]);

        ActivityLog::create([
            'action' => 'reservation_created',
            'description' => "Nouvelle réservation pour {$request->customer_name} dans la salle {$session->room->name}",
            'loggable_id' => $reservation->id,
            'loggable_type' => Reservation::class,
            'payload' => [
                'room_id' => $session->room_id,
                'date' => $request->date,
                'attendees' => $request->attendee_count
            ]
        ]);

        return response()->json([
            'status' => 'success',
            'message' => "La session a été réservée avec succès. Vous recevrez un mail de confirmation sous peu.",
            'data' => [
                'reservation' => $reservation,
                'session' => $session
            ]
        ], 200);
    }
}
