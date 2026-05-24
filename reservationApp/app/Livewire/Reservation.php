<?php

namespace App\Livewire;

use App\Mail\ReservationConfirmation;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Mail;
use Livewire\Attributes\Layout;
use Livewire\Component;

#[Layout('layouts.app')]
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
            $this->addError('selectedEndTime', 'The end time must be after the start time.');
            return;
        }

        $this->step = 'checking';
    }

    public function checkAvailability()
    {
        $this->roomFound = rand(1, 10) <= 7;

        if ($this->roomFound) {
            if (empty($this->email)) {
                $this->resultMessage = 'No email address provided.';
                $this->step = 'result';
                return;
            }

            try {
                Mail::mailer('smtp')->to($this->email)->send(new ReservationConfirmation(
                    name: $this->name,
                    email: $this->email,
                    date: $this->selectedDate,
                    startTime: $this->selectedStartTime,
                    endTime: $this->selectedEndTime,
                    people: $this->peopleCount,
                ));
                $this->resultMessage = 'A room has been found for your reservation! You will receive your confirmation email.';
            } catch (\Throwable $e) {
                Log::error('Mail send failed: ' . $e->getMessage(), [
                    'email' => $this->email,
                    'host' => config('mail.mailers.smtp.host'),
                    'port' => config('mail.mailers.smtp.port'),
                    'user' => config('mail.mailers.smtp.username'),
                ]);
                $this->resultMessage = 'Room found but email could not be sent. Please contact support.';
            }
        } else {
            $this->resultMessage = 'Sorry, no rooms are available for this time slot. Please try another time.';
        }

        $this->step = 'result';
    }

    public function resetForm()
    {
        $this->reset(['name', 'email', 'selectedDate', 'selectedStartTime', 'selectedEndTime', 'peopleCount', 'step', 'roomFound', 'resultMessage']);
    }

    public function render()
    {
        return view('livewire.reservation');
    }
}
