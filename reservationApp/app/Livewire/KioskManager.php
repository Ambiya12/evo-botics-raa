<?php

namespace App\Livewire;

use App\Models\Reservation;
use Livewire\Component;

class KioskManager extends Component
{
    public $step = 'welcome'; // welcome, validating, result, guide
    public $scanData = '';
    public $resultStatus = '';
    public $reservation = [];

    public function goToStep($stepName)
    {
        $this->step = $stepName;

        // Si on arrive sur "Result" ou "Guide", on déclenche un timer pour la suite
        if ($stepName === 'result') {
            $nextStep = $this->resultStatus === 'success' ? 'guide' : 'welcome';
            $this->dispatch('start-timer', nextStep: $nextStep, delay: 5000); // 5 sec
        } elseif ($stepName === 'guide') {
            $this->dispatch('start-timer', nextStep: 'welcome', delay: 10000); // 10 sec
        }
    }

    // Simulation de la validation du scan
    public function processScan($data)
    {
        $this->scanData = $data;
        $this->step = 'validating';

        $decoded = json_decode($data, true);

        if (!$decoded || !isset($decoded['payload']) || !isset($decoded['signature'])) {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        $payload = $decoded['payload'];
        $signature = $decoded['signature'];
        $secret = config('app.key');
        $expected = hash_hmac('sha256', $payload, $secret);

        if (!hash_equals($expected, $signature)) {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        $reservationData = json_decode($payload, true) ?? [];
        $uuid = $reservationData['uuid'] ?? null;

        $reservation = $uuid ? Reservation::where('uuid', $uuid)->first() : null;

        if (!$reservation) {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        if ($reservation->status === 'validated') {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        if ($reservation->status === 'cancelled' || $reservation->status === 'expired') {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        $reservation->update([
            'status' => 'validated',
            'validated_at' => now(),
        ]);

        $this->reservation = $reservationData;
        $this->resultStatus = 'success';
        $this->goToStep('result');
    }

    public function mount()
    {
        if (request()->has('step')) {
            $this->step = request()->query('step');
            $this->resultStatus = request()->query('status', 'error');
        }
    }

    public function render()
    {
        return view('livewire.kiosk-manager');
    }
}