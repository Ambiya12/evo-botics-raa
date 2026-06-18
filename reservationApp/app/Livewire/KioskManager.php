<?php

namespace App\Livewire;

use App\Models\ActivityLog;
use App\Models\Reservation;
use App\Support\ReservationQrPayload;
use Livewire\Component;

class KioskManager extends Component
{
    public $step = 'welcome'; // welcome, validating, result, guide
    public $scanData = '';
    public $resultStatus = '';
    public $reservation = [];
    public $scanMode = 'robot';
    public $robotRosbridgeUrl = '';
    public $robotStatusMessage = '';
    public $robotErrorCode = null;

    public function goToStep($stepName)
    {
        $this->step = $stepName;

        if ($stepName === 'result') {
            $nextStep = $this->resultStatus === 'success' ? 'guide' : 'welcome';
            $this->dispatch('start-timer', nextStep: $nextStep, delay: 5000);
        } elseif ($stepName === 'guide') {
            $this->dispatch('start-timer', nextStep: 'welcome', delay: 10000);
        }
    }

    public function processScan($data)
    {
        $this->scanData = $data;
        $this->step = 'validating';
        $this->robotStatusMessage = __('QR detected, validating your reservation...');

        $decoded = json_decode($data, true);

        if (!$decoded || !is_array($decoded)) {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        if (($decoded['type'] ?? null) === 'reservation' && isset($decoded['signature'])) {
            if (!ReservationQrPayload::verify($decoded) || !$this->validateBrowserReservation($data)) {
                $this->resultStatus = 'error';
                $this->goToStep('result');
                return;
            }

            $this->resultStatus = 'success';
            $this->goToStep('result');
            return;
        }

        if (!isset($decoded['payload']) || !isset($decoded['signature'])) {
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

        if (!$this->validateBrowserReservation($data)) {
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        $this->resultStatus = 'success';
        $this->goToStep('result');
    }

    public function applyRobotQrStatus($status)
    {
        if (is_string($status)) {
            $status = json_decode($status, true);
        }

        if (!is_array($status)) {
            return;
        }

        $state = $status['state'] ?? 'waiting';
        $this->robotStatusMessage = $status['message'] ?? '';
        $this->robotErrorCode = $status['error_code'] ?? null;

        if (in_array($state, ['scanned', 'validating'], true)) {
            $this->resultStatus = '';
            $this->step = 'validating';
            return;
        }

        if ($state === 'success') {
            $this->reservation = $this->normalizeRobotReservation($status['reservation'] ?? []);
            $this->resultStatus = 'success';
            $this->goToStep('result');
            return;
        }

        if ($state === 'error') {
            $this->reservation = [];
            $this->resultStatus = 'error';
            $this->goToStep('result');
            return;
        }

        $this->resultStatus = '';
        $this->reservation = [];
        $this->step = 'welcome';
    }

    public function mount()
    {
        $this->scanMode = request()->query('scan') === 'browser' ? 'browser' : 'robot';
        $this->robotRosbridgeUrl = config('services.robot.rosbridge_url');
        $this->robotStatusMessage = __('Waiting for the robot camera...');

        if (request()->has('step')) {
            $this->step = request()->query('step');
            $this->resultStatus = request()->query('status', 'error');
        }
    }

    public function render()
    {
        return view('livewire.kiosk-manager');
    }

    private function validateBrowserReservation(string $qrPayload): bool
    {
        $uuid = ReservationQrPayload::uuidFromQrPayload($qrPayload);
        if (!$uuid) {
            return false;
        }

        $reservation = Reservation::with('bookingSession.room')->where('uuid', $uuid)->first();
        if (!$reservation || $reservation->status !== 'pending') {
            return false;
        }

        $reservation->update([
            'status' => 'validated',
            'validated_at' => now(),
        ]);

        ActivityLog::create([
            'action' => 'reservation_validated',
            'description' => "Réservation validée pour {$reservation->customer_name}",
            'loggable_id' => $reservation->id,
            'loggable_type' => Reservation::class,
            'payload' => [
                'validated_at' => $reservation->validated_at,
                'uuid' => $reservation->uuid,
                'method' => 'Browser QR Scan',
            ],
        ]);

        $this->reservation = $this->normalizeRobotReservation([
            'uuid' => $reservation->uuid,
            'customer_name' => $reservation->customer_name,
            'room' => $reservation->bookingSession?->room?->name,
            'date' => optional($reservation->bookingSession?->date)->format('Y-m-d'),
            'start_at' => $reservation->bookingSession?->start_at,
            'end_at' => $reservation->bookingSession?->end_at,
        ]);

        return true;
    }

    private function normalizeRobotReservation(array $reservation): array
    {
        return [
            'uuid' => $reservation['uuid'] ?? null,
            'name' => $reservation['customer_name'] ?? $reservation['name'] ?? '',
            'room' => $reservation['room'] ?? null,
            'date' => $reservation['date'] ?? '',
            'startTime' => $reservation['start_at'] ?? $reservation['startTime'] ?? '',
            'endTime' => $reservation['end_at'] ?? $reservation['endTime'] ?? '',
        ];
    }
}
