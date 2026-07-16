<?php

namespace App\Http\Controllers\Admin;

use App\Http\Controllers\Controller;
use App\Models\BookingSession;
use App\Models\Room;
use App\Models\ActivityLog;
use Illuminate\Http\Request;
use Inertia\Inertia;

class AdminSessionController extends Controller
{
    public function index()
    {
        return Inertia::render('Admin/Sessions/Index', [
            'sessions' => BookingSession::with('room')
                ->orderBy('date', 'desc')
                ->orderBy('start_at', 'asc')
                ->get()
                ->map(function ($session) {
                    return [
                        'id' => $session->id,
                        'date' => $session->date,
                        'start_at' => substr($session->start_at, 0, 5),
                        'end_at' => substr($session->end_at, 0, 5),
                        'room_name' => $session->room ? $session->room->name : 'Aucune salle',
                        'is_available' => $session->is_available,
                    ];
                }),
            'rooms' => Room::all(['id', 'name']),
        ]);
    }

    public function store(Request $request)
    {
        $validated = $request->validate([
            'room_id' => 'required|exists:rooms,id',
            'date' => 'required|date|after_or_equal:today',
            'start_at' => 'required|date_format:H:i',
            'end_at' => 'required|date_format:H:i|after:start_at',
        ]);

        BookingSession::create($validated);

        return redirect()->back()->with('success', 'Session de réservation créée avec succès.');
    }

    public function destroy(BookingSession $bookingSession)
    {
        $bookingSession->delete();

        return redirect()->back()->with('success', 'Session supprimée avec succès.');
    }
}

?>