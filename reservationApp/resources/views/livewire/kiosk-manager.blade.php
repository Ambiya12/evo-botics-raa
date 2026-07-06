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
                    <p
                        id="robot-connection-status"
                        class="mt-3 text-lg font-medium text-amber-600"
                        role="status"
                        aria-live="polite"
                    >
                        {{ __('Connecting to the robot...') }}
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
        <x-spinner />
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
        let robotQrConnectionTimer = null;
        let robotQrStatusQueue = Promise.resolve();
        let robotQrReconnectAttempt = 0;

        const kioskScanMode = @js($scanMode);
        const robotRosbridgeUrl = @js($robotRosbridgeUrl);
        const robotQrTopic = '/reception/qr/status';
        const robotConnectionMessages = {
            connecting: @js(__('Connecting to the robot...')),
            connected: @js(__('Robot connected. Waiting for a QR code...')),
            disconnected: @js(__('Robot connection lost. Reconnecting...')),
        };

        function updateRobotConnectionStatus(state) {
            const el = document.getElementById('robot-connection-status');
            if (!el) return;

            el.textContent = robotConnectionMessages[state] ?? robotConnectionMessages.connecting;
            el.classList.toggle('text-green-600', state === 'connected');
            el.classList.toggle('text-amber-600', state !== 'connected');
        }

        function clearRobotConnectionTimer() {
            if (!robotQrConnectionTimer) return;

            clearTimeout(robotQrConnectionTimer);
            robotQrConnectionTimer = null;
        }

        function scheduleRobotQrReconnect() {
            if (kioskScanMode !== 'robot' || robotQrReconnectTimer) return;

            const delay = Math.min(1000 * (2 ** robotQrReconnectAttempt), 15000);
            robotQrReconnectAttempt += 1;
            robotQrReconnectTimer = setTimeout(() => {
                robotQrReconnectTimer = null;
                connectRobotQrStatus();
            }, delay);
        }

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

            updateRobotConnectionStatus('connecting');

            let socket;
            try {
                socket = new WebSocket(robotRosbridgeUrl);
            } catch (err) {
                console.error('Robot QR WebSocket setup error:', err);
                updateRobotConnectionStatus('disconnected');
                scheduleRobotQrReconnect();
                return;
            }

            robotQrSocket = socket;
            robotQrConnectionTimer = setTimeout(() => {
                if (socket.readyState === WebSocket.CONNECTING) {
                    socket.close();
                }
            }, 5000);

            socket.onopen = () => {
                clearRobotConnectionTimer();
                robotQrReconnectAttempt = 0;
                updateRobotConnectionStatus('connected');
                socket.send(JSON.stringify({
                    op: 'subscribe',
                    id: 'kiosk:reception_qr_status',
                    topic: robotQrTopic,
                    type: 'std_msgs/msg/String'
                }));
            };

            socket.onmessage = (event) => {
                try {
                    const envelope = JSON.parse(event.data);
                    const rawStatus = envelope?.msg?.data;
                    if (envelope.op !== 'publish' || envelope.topic !== robotQrTopic || !rawStatus) return;
                    const status = JSON.parse(rawStatus);

                    robotQrStatusQueue = robotQrStatusQueue
                        .catch(() => {})
                        .then(() => $wire.applyRobotQrStatus(status))
                        .catch((err) => {
                            console.error('Robot QR status update error:', err);
                        });
                } catch (err) {
                    console.error('Robot QR status parse error:', err);
                }
            };

            socket.onclose = () => {
                clearRobotConnectionTimer();
                if (robotQrSocket === socket) {
                    robotQrSocket = null;
                    updateRobotConnectionStatus('disconnected');
                    scheduleRobotQrReconnect();
                }
            };

            socket.onerror = (err) => {
                console.error('Robot QR WebSocket error:', err);
                try { socket.close(); } catch (e) {}
            };
        }

        function stopRobotQrStatus() {
            clearRobotConnectionTimer();

            if (robotQrReconnectTimer) {
                clearTimeout(robotQrReconnectTimer);
                robotQrReconnectTimer = null;
            }

            if (robotQrSocket) {
                const socket = robotQrSocket;
                robotQrSocket = null;
                try {
                    if (socket.readyState === WebSocket.OPEN) {
                        socket.send(JSON.stringify({
                            op: 'unsubscribe',
                            id: 'kiosk:reception_qr_status',
                            topic: robotQrTopic
                        }));
                    }
                    socket.close();
                } catch (e) {}
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
