<div>
<div class="fixed top-4 right-4 z-50">
    <x-language-switcher :current="app()->getLocale()" />
</div>

@if($step === 'welcome')
    <div class="screen">
        <div class="flex min-h-screen items-center justify-center overflow-hidden bg-white px-6 font-robot">
            <div class="w-full max-w-5xl text-center">
                <p class="text-5xl font-bold text-gray-900 md:text-8xl">
                    {{ __('Welcome to') }}
                </p>

                <h1 class="mt-4 text-5xl font-bold text-gray-900 md:text-7xl">
                    EVO<span class="text-blue-500">BOTICS</span>
                </h1>

                <p class="mt-8 text-3xl text-gray-500 md:text-5xl">
                    {{ __('Show your reservation QR code') }}
                </p>

                @if($scanMode === 'robot')
                    <div class="mx-auto mt-12 flex h-64 w-64 items-center justify-center rounded-full border-8 border-dashed border-blue-300 bg-blue-50">
                        <div class="h-28 w-28 animate-pulse rounded-full bg-blue-500"></div>
                    </div>

                    <p class="mt-8 text-2xl font-semibold text-blue-600">
                        {{ $robotStatusMessage ?: __('Waiting for the robot camera...') }}
                    </p>
                    <p class="mt-3 text-xl text-gray-400">
                        {{ __('Keep the QR code steady in front of me.') }}
                    </p>
                @else
                    <div class="mt-10 flex items-center justify-center">
                        <div id="qr-reader" class="h-64 w-64 overflow-hidden rounded-xl border-4 border-dashed border-gray-400 -scale-x-100 [&_video]:h-full [&_video]:w-full [&_video]:object-cover"></div>
                    </div>
                    <p class="mt-6 text-xl text-gray-400">
                        {{ __('Browser camera fallback mode') }}
                    </p>
                @endif
            </div>
        </div>
    </div>

@elseif($step === 'validating')
    <div class="screen flex min-h-screen flex-col items-center justify-center overflow-hidden bg-white px-6 text-center font-robot">
        <svg class="size-24 animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <p class="mt-8 text-4xl font-semibold text-gray-700 md:text-6xl">
            {{ __('QR detected') }}
        </p>
        <p class="mt-4 text-3xl text-gray-500 md:text-5xl">
            {{ $robotStatusMessage ?: __('Validating your reservation...') }}
        </p>
    </div>

@elseif($step === 'result')
    <div class="screen flex min-h-screen flex-col items-center justify-center overflow-hidden px-6 text-center font-robot {{ $resultStatus === 'success' ? 'bg-green-50' : 'bg-red-50' }}">
        @if($resultStatus === 'success')
            <svg class="size-24 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <h1 class="mt-6 text-6xl font-bold text-green-700 md:text-8xl">{{ __('Success') }}</h1>
            <p class="mt-4 text-3xl text-green-600 md:text-5xl">{{ __('Your reservation has been validated.') }}</p>

            @if(!empty($reservation))
                <div class="mt-8 space-y-2 text-2xl text-green-700 md:text-4xl">
                    @if(!empty($reservation['name']))
                        <p>{{ $reservation['name'] }}</p>
                    @endif
                    @if(!empty($reservation['room']))
                        <p>{{ $reservation['room'] }}</p>
                    @endif
                    @if(!empty($reservation['date']) || !empty($reservation['startTime']) || !empty($reservation['endTime']))
                        <p>{{ $reservation['date'] }} {{ $reservation['startTime'] }} - {{ $reservation['endTime'] }}</p>
                    @endif
                </div>
            @endif
        @else
            <svg class="size-24 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
            </svg>
            <h1 class="mt-6 text-6xl font-bold text-red-700 md:text-8xl">{{ __('Error') }}</h1>
            <p class="mt-4 text-3xl text-red-600 md:text-5xl">
                {{ $robotStatusMessage ?: __('Your QR code is invalid or expired.') }}
            </p>
            <p class="mt-4 text-2xl text-red-500 md:text-4xl">{{ __('Please verify with my colleagues.') }}</p>
        @endif
    </div>

@elseif($step === 'guide')
    <div class="screen">
        <div class="flex min-h-screen flex-col items-center justify-center overflow-hidden bg-white px-6 text-center font-robot">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-24 animate-bounce text-blue-500">
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 18.75 7.5-7.5 7.5 7.5" />
                <path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 7.5-7.5 7.5 7.5" />
            </svg>
            <span class="mt-8 text-6xl text-blue-500 md:text-8xl">{{ __('Please follow me!') }}</span>
            <span class="mt-6 text-3xl text-gray-700 md:text-5xl">
                {{ __('I will drive you to your room') }}
            </span>
        </div>
    </div>
@endif
</div>

@script
    <script>
        let scannerInstance = null;
        let robotQrSocket = null;
        let robotQrReconnectTimer = null;

        const kioskScanMode = @js($scanMode);
        const robotRosbridgeUrl = @js($robotRosbridgeUrl);
        const robotQrTopic = '/reception/qr/status';

        async function startScanner() {
            const el = document.getElementById('qr-reader');
            if (!el || kioskScanMode !== 'browser') return;

            if (scannerInstance) {
                try { await scannerInstance.stop(); } catch (e) {}
                scannerInstance = null;
            }

            scannerInstance = new Html5Qrcode('qr-reader');
            try {
                await scannerInstance.start(
                    { facingMode: 'environment' },
                    { fps: 10, qrbox: { width: 250, height: 250 } },
                    async (decodedText) => {
                        try { await scannerInstance.stop(); } catch (e) {}
                        scannerInstance = null;
                        $wire.processScan(decodedText);
                    }
                );
            } catch (err) {
                console.error('QR scanner error:', err);
                setTimeout(startScanner, 2000);
            }
        }

        async function stopScanner() {
            if (scannerInstance) {
                try { await scannerInstance.stop(); } catch (e) {}
                scannerInstance = null;
            }
        }

        function connectRobotQrStatus() {
            if (kioskScanMode !== 'robot' || !robotRosbridgeUrl || robotQrSocket) return;

            robotQrSocket = new WebSocket(robotRosbridgeUrl);

            robotQrSocket.onopen = () => {
                robotQrSocket.send(JSON.stringify({
                    op: 'subscribe',
                    id: 'kiosk:reception_qr_status',
                    topic: robotQrTopic,
                    type: 'std_msgs/msg/String',
                    throttle_rate: 100
                }));
            };

            robotQrSocket.onmessage = (event) => {
                try {
                    const envelope = JSON.parse(event.data);
                    const rawStatus = envelope?.msg?.data;
                    if (envelope.op !== 'publish' || envelope.topic !== robotQrTopic || !rawStatus) return;
                    $wire.applyRobotQrStatus(JSON.parse(rawStatus));
                } catch (err) {
                    console.error('Robot QR status parse error:', err);
                }
            };

            robotQrSocket.onclose = () => {
                robotQrSocket = null;
                if (kioskScanMode === 'robot') {
                    robotQrReconnectTimer = setTimeout(connectRobotQrStatus, 3000);
                }
            };

            robotQrSocket.onerror = () => {
                try { robotQrSocket.close(); } catch (e) {}
            };
        }

        function stopRobotQrStatus() {
            if (robotQrReconnectTimer) {
                clearTimeout(robotQrReconnectTimer);
                robotQrReconnectTimer = null;
            }

            if (robotQrSocket) {
                try {
                    robotQrSocket.send(JSON.stringify({
                        op: 'unsubscribe',
                        id: 'kiosk:reception_qr_status',
                        topic: robotQrTopic
                    }));
                    robotQrSocket.close();
                } catch (e) {}
                robotQrSocket = null;
            }
        }

        function syncKioskScanMode() {
            if (kioskScanMode === 'browser' && $wire.step === 'welcome') {
                stopRobotQrStatus();
                setTimeout(startScanner, 300);
                return;
            }

            stopScanner();
            if (kioskScanMode === 'robot') {
                connectRobotQrStatus();
            }
        }

        Livewire.on('start-timer', (event) => {
            const payload = Array.isArray(event) ? event[0] : event;
            setTimeout(() => {
                Promise.resolve($wire.goToStep(payload.nextStep)).finally(() => {
                    setTimeout(syncKioskScanMode, 300);
                });
            }, payload.delay);
        });

        document.addEventListener('livewire:navigated', syncKioskScanMode);
        syncKioskScanMode();
    </script>
@endscript
