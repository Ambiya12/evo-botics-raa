<div>
@if($step === 'welcome')
	<div class="screen">
		<div class="flex items-center justify-center min-h-screen bg-white overflow-hidden relative">
			<div class="absolute w-64 h-64 bg-blue-600 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>

			<div class="text-center z-10 font-robot"
			     x-data="{ visible: false }"
			     x-init="setTimeout(() => visible = true, 100)">

				<div x-show="visible"
				     x-transition:enter="transition ease-out duration-1000"
				     x-transition:enter-start="opacity-0 translate-y-10"
				     x-transition:enter-end="opacity-100 translate-y-0">
					<p class="-translate-y-20 text-black-400 font-bold text-8xl mt-20">
						Welcome to
					</p>

					<h1 class="-translate-y-10 text-6xl font-bold text-gray-900 tracking-tighter">
						EVO<span class="text-blue-500">BOTICS</span>
					</h1>

					<p class="text-gray-400 text-2xl">
						Please show me your reservation <span class="text-blue-500">QR code</span> to me to get started!
					</p>
					
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-8 mx-auto 
					animate-bounce text-gray-400 mt-2">
						<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 5.25 7.5 7.5 7.5-7.5m-15 6 7.5 7.5 7.5-7.5" />
					</svg>

					<div class="flex items-center justify-center">
						<div id="qr-reader" class="w-64 h-64 rounded-xl overflow-hidden border-4 border-dashed border-gray-400 -scale-x-100 [&_video]:w-full [&_video]:h-full [&_video]:object-cover"></div>
					</div>
				</div>
			</div>
		</div>
	</div>
	
@elseif($step === 'validating')

	<div class="flex flex-col items-center justify-center min-h-screen bg-white overflow-hidden font-robot screen">
		<svg class="size-20 animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
			<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
			<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
		</svg>
		<p class="text-gray-500 text-5xl mt-2">Validation in progress...</p>
		<p class="text-gray-500 text-5xl mt-2">Please wait...</p>
	</div>

@elseif($step === 'result')
	<div class="flex flex-col items-center justify-center min-h-screen {{ $resultStatus === 'success' ? 'bg-green-50' : 'bg-red-50' }} font-robot screen">
		@if($resultStatus === 'success')
			<svg class="size-20 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<h1 class="mt-4 text-8xl font-bold text-green-700">Success</h1>
			<p class="mt-2 text-green-600 text-4xl">Your reservation has been successfully validated!</p>
			@if(!empty($reservation))
				<p class="mt-2 text-green-500 text-2xl">{{ $reservation['name'] }} • {{ $reservation['date'] }} • {{ $reservation['startTime'] }} — {{ $reservation['endTime'] }}</p>
			@endif
		@else
			<svg class="size-20 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
			</svg>
			<h1 class="mt-4 text-8xl font-bold text-red-700">Error</h1>
			<p class="mt-2 text-red-600 text-5xl">Your QR code is invalid or expired.</p>
			<p class="mt-2 text-red-600 text-5xl">Please verify with my colleagues!</p>
		@endif
	</div>

@elseif($step === 'guide')
	<div class="screen">
		<div class="flex flex-col items-center justify-center min-h-screen bg-white overflow-hidden font-robot">
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-20 text-blue-500 animate-bounce">
				<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 18.75 7.5-7.5 7.5 7.5" />
				<path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 7.5-7.5 7.5 7.5" />
			</svg>
			<span class="text-8xl text-blue-500">Please follow me!</span>
			<span class="text-5xl flex items-center">
			    I will drive you to your room
			    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-12 ml-2">
			        <path stroke-linecap="round" stroke-linejoin="round" d="M15.182 15.182a4.5 4.5 0 0 1-6.364 0M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM9.75 9.75c0 .414-.168.75-.375.75S9 10.164 9 9.75 9.168 9 9.375 9s.375.336.375.75Zm-.375 0h.008v.015h-.008V9.75Zm5.625 0c0 .414-.168.75-.375.75s-.375-.336-.375-.75.168-.75.375-.75.375.336.375.75Zm-.375 0h.008v.015h-.008V9.75Z" />
			    </svg>
			</span>
		</div>
	</div>
@endif
</div>

@script
    <script>
        let scannerInstance = null;

        async function startScanner() {
            const el = document.getElementById('qr-reader');
            if (!el) return;

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

        Livewire.on('start-timer', (event) => {
            setTimeout(() => {
                $wire.goToStep(event.nextStep);
            }, event.delay);
        });

        document.addEventListener('livewire:navigated', () => {
            if ($wire.step === 'welcome') {
                setTimeout(startScanner, 300);
            } else {
                stopScanner();
            }
        });
    </script>
@endscript