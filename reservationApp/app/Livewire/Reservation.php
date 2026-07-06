<?php

namespace App\Livewire;

use App\Mail\ReservationConfirmation;
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

    public function resetForm()
    {
        $this->reset(['name', 'email', 'selectedDate', 'selectedStartTime', 'selectedEndTime', 'peopleCount', 'step', 'roomFound', 'resultMessage']);
    }

    public function render()
    {
        return view('livewire.reservation');
    }
}
