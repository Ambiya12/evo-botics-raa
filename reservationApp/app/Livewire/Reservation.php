<?php

namespace App\Livewire;

use App\Mail\ReservationConfirmed;
use App\Models\ActivityLog;
use App\Models\BookingSession;
use App\Models\Reservation as ReservationModel;
use App\Support\ReservationQrPayload;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;
use Livewire\Attributes\Layout;
use Livewire\Component;

class Reservation extends Component
{
    public $name = '';

    public $email = '';

    public $selectedDate = '';

    public $selectedStartTime = '';

    public $selectedEndTime = '';

    public $peopleCount = 1;

    public $step = 'form';

    public $roomFound = false;

    public $resultMessage = '';

    public $qrCodeDataUri = '';

    public $reservedRoomName = '';

    public $confirmationEmailSent = false;

    public function reserve()
    {
        $this->validate([
            'name' => ['required', 'string', 'max:255', 'regex:/^[^=<>&"\']*$/'],
            'email' => 'required|email|max:255',
            'selectedDate' => 'required|date|after:yesterday',
            'selectedStartTime' => ['required', 'regex:/^(0[9]|1[0-9]):00$/'],
            'selectedEndTime' => ['required', 'regex:/^(1[0-9]|20):00$/'],
            'peopleCount' => 'required|integer|min:1|max:30',
        ]);

        $startHour = (int) explode(':', $this->selectedStartTime)[0];
        $endHour = (int) explode(':', $this->selectedEndTime)[0];

        if ($startHour >= $endHour) {
            $this->addError('selectedEndTime', __('The end time must be after the start time.'));

            return;
        }

        $this->step = 'checking';
    }

    public function checkAvailability()
    {
        $this->validate([
            'name' => ['required', 'string', 'max:255', 'regex:/^[^=<>&"\']*$/'],
            'email' => 'required|email|max:255',
            'selectedDate' => 'required|date|after:yesterday',
            'selectedStartTime' => ['required', 'regex:/^(0[9]|1[0-9]):00$/'],
            'selectedEndTime' => ['required', 'regex:/^(1[0-9]|20):00$/'],
            'peopleCount' => 'required|integer|min:1|max:30',
        ]);

        $startHour = (int) explode(':', $this->selectedStartTime)[0];
        $endHour = (int) explode(':', $this->selectedEndTime)[0];

        if ($startHour >= $endHour) {
            $this->addError('selectedEndTime', __('The end time must be after the start time.'));
            $this->step = 'form';

            return;
        }

        $reservation = DB::transaction(function () {
            $startTimes = array_values(array_unique([
                $this->selectedStartTime,
                date('H:i:s', strtotime($this->selectedStartTime)),
            ]));
            $endTimes = array_values(array_unique([
                $this->selectedEndTime,
                date('H:i:s', strtotime($this->selectedEndTime)),
            ]));

            $session = BookingSession::query()
                ->with('room')
                ->whereDate('date', $this->selectedDate)
                ->whereIn('start_at', $startTimes)
                ->whereIn('end_at', $endTimes)
                ->where('is_available', true)
                ->whereHas('room', fn ($query) => $query->where('max_capacity', '>=', $this->peopleCount))
                ->orderBy('id')
                ->lockForUpdate()
                ->first();

            if (! $session) {
                ActivityLog::create([
                    'action' => 'booking_failed_no_slot',
                    'description' => "Échec : Aucun créneau libre le {$this->selectedDate} à {$this->selectedStartTime}",
                    'payload' => [
                        'date' => $this->selectedDate,
                        'start_at' => $this->selectedStartTime,
                        'end_at' => $this->selectedEndTime,
                        'attendee_count' => $this->peopleCount,
                        'customer_email' => $this->email,
                    ],
                ]);

                return null;
            }

            $reservation = ReservationModel::create([
                'user_id' => auth()->id(),
                'customer_name' => $this->name,
                'customer_email' => $this->email,
                'status' => 'pending',
                'attendee_count' => $this->peopleCount,
                'booking_session_id' => $session->id,
            ]);

            $session->update(['is_available' => false]);
            $reservation->load('bookingSession.room');

            ActivityLog::create([
                'action' => 'reservation_created',
                'description' => "Nouvelle réservation pour {$this->name} dans la salle {$session->room->name}",
                'loggable_id' => $reservation->id,
                'loggable_type' => ReservationModel::class,
                'payload' => [
                    'room_id' => $session->room_id,
                    'date' => $this->selectedDate,
                    'attendees' => $this->peopleCount,
                    'source' => 'reservation_page',
                ],
            ]);

            return $reservation;
        });

        if (! $reservation) {
            $this->roomFound = false;
            $this->qrCodeDataUri = '';
            $this->reservedRoomName = '';
            $this->resultMessage = __('Sorry, no rooms are available for this time slot. Please try another time.');
            $this->step = 'result';

            return;
        }

        $this->roomFound = true;
        $this->reservedRoomName = $reservation->bookingSession?->room?->name ?? '';
        $this->qrCodeDataUri = ReservationQrPayload::dataUri(
            ReservationQrPayload::forReservation($reservation),
            360
        );
        $this->confirmationEmailSent = false;
        $this->resultMessage = __('A room has been found for your reservation! Show this QR code to the robot camera when you arrive.');

        try {
            Mail::to($reservation->customer_email)->send(new ReservationConfirmed($reservation));
            $this->confirmationEmailSent = true;

            ActivityLog::create([
                'action' => 'email_sent',
                'description' => "Email de confirmation envoyé à {$reservation->customer_email}",
                'loggable_id' => $reservation->id,
                'loggable_type' => ReservationModel::class,
            ]);
        } catch (\Throwable $e) {
            Log::error('Mail send failed: '.$e->getMessage(), [
                'email' => $reservation->customer_email,
                'host' => config('mail.mailers.smtp.host'),
                'port' => config('mail.mailers.smtp.port'),
                'user' => config('mail.mailers.smtp.username'),
            ]);
        }

        $this->step = 'result';
    }

    public function resetForm()
    {
        $this->reset([
            'name',
            'email',
            'selectedDate',
            'selectedStartTime',
            'selectedEndTime',
            'peopleCount',
            'step',
            'roomFound',
            'resultMessage',
            'qrCodeDataUri',
            'reservedRoomName',
            'confirmationEmailSent',
        ]);
    }

    public function render()
    {
        return view('livewire.reservation');
    }
}
