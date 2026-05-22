<?php

namespace App\Livewire;

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
        // Simulation : 70% de chance qu'une salle soit trouvée
        $this->roomFound = rand(1, 10) <= 7;
        $this->resultMessage = $this->roomFound
            ? 'A room has been found for your reservation! You will receive your confirmation email.'
            : 'Sorry, no rooms are available for this time slot. Please try another time.';
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
