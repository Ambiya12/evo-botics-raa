<?php

namespace App\Livewire;

use Livewire\Component;

class KioskManager extends Component
{
    public $step = 'welcome'; // welcome, validating, result, guide
    public $scanData = '';
    public $resultStatus = '';

    public function goToStep($stepName)
    {
        $this->step = $stepName;

        // Si on arrive sur "Result" ou "Guide", on déclenche un timer pour la suite
        if ($stepName === 'result') {
            $this->dispatch('start-timer', nextStep: 'guide', delay: 5000); // 5 sec
        } elseif ($stepName === 'guide') {
            $this->dispatch('start-timer', nextStep: 'welcome', delay: 10000); // 10 sec
        }
    }

    // Simulation de la validation du scan
    public function processScan($data)
    {
        $this->scanData = $data;
        $this->step = 'validating';

        // Logique de validation (API, DB, etc.)
        sleep(2); // Simulation

        $this->resultStatus = 'success';
        $this->goToStep('result');
    }

//    public function mount()
//    {
//        // Permet d'aller sur /kiosk?debugStep=guide pour voir l'écran guide direct
//        if (request()->has('debugStep')) {
//            $this->step = request()->query('debugStep');
//            $this->resultStatus = request()->query('debugStatus', 'error');
//        }
//    }

    public function render()
    {
        return view('livewire.kiosk-manager');
    }
}