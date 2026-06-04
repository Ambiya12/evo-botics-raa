<div class="min-h-full">

    @php
        $__t = json_decode(file_get_contents(lang_path(app()->getLocale().'.json')), true) ?? [];
        $__locale = app()->getLocale();
    @endphp

    <script>
        document.addEventListener('alpine:init', () => {
            Alpine.data('reservationForm', () => ({
                t: @json($__t),
                locale: '{{ $__locale }}',
                month: new Date().getMonth(),
                year: new Date().getFullYear(),
                localName: '',
                localEmail: '',
                localDate: '',
                localStartTime: '',
                localEndTime: '',
                localPeople: 1,
                showTimePicker: false,
                nameError: '',
                emailError: '',

                validate() {
                    let valid = true;
                    this.nameError = '';
                    this.emailError = '';
                    if (!this.localName || this.localName.trim().length < 2) {
                        this.nameError = this.t['Please enter a valid name (at least 2 characters).'] || 'Please enter a valid name (at least 2 characters).';
                        valid = false;
                    } else if (/[=<>&'\x22]/.test(this.localName)) {
                        this.nameError = this.t['Name contains invalid characters.'] || 'Name contains invalid characters.';
                        valid = false;
                    }
                    if (!this.localEmail || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(this.localEmail)) {
                        this.emailError = this.t['Please enter a valid email address.'] || 'Please enter a valid email address.';
                        valid = false;
                    }
                    return valid;
                },
                async book() {
                    if (!this.validate()) return;
                    await this.$wire.reserve();
                    setTimeout(() => this.$wire.checkAvailability(), 3000);
                },

                get daysInMonth() {
                    return new Date(this.year, this.month + 1, 0).getDate();
                },
                get firstDay() {
                    return new Date(this.year, this.month, 1).getDay();
                },
                get monthName() {
                    return new Date(this.year, this.month).toLocaleString(this.locale, { month: 'long' });
                },
                get formattedDate() {
                    if (!this.localDate) return '-';
                    const [y, m, d] = this.localDate.split('-');
                    return new Date(y, m - 1, d).toLocaleDateString(this.locale, {
                        weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                    });
                },
                prevMonth() {
                    if (this.month === 0) { this.month = 11; this.year--; }
                    else { this.month--; }
                },
                nextMonth() {
                    if (this.month === 11) { this.month = 0; this.year++; }
                    else { this.month++; }
                },
                isPast(day) {
                    const date = new Date(this.year, this.month, day);
                    const today = new Date();
                    today.setHours(0, 0, 0, 0);
                    return date <= today;
                },
                get endTimeOptions() {
                    if (!this.localStartTime) return [];
                    const start = parseInt(this.localStartTime.split(':')[0]);
                    return Array.from({length: 20 - start}, (_, i) => start + 1 + i);
                },
                async selectDate(day) {
                    if (this.isPast(day)) return;
                    const d = `${this.year}-${String(this.month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
                    this.localDate = d;
                    this.localStartTime = '';
                    this.localEndTime = '';
                    await this.$wire.set('selectedDate', d);
                    await this.$wire.set('selectedStartTime', '');
                    await this.$wire.set('selectedEndTime', '');
                    this.showTimePicker = true;
                },
                async selectStartTime(hour) {
                    const t = String(hour).padStart(2, '0') + ':00';
                    this.localStartTime = t;
                    await this.$wire.set('selectedStartTime', t);
                    const endHour = Math.min(hour + 1, 20);
                    const endT = String(endHour).padStart(2, '0') + ':00';
                    this.localEndTime = endT;
                    await this.$wire.set('selectedEndTime', endT);
                },
                async selectEndTime(hour) {
                    const t = String(hour).padStart(2, '0') + ':00';
                    this.localEndTime = t;
                    await this.$wire.set('selectedEndTime', t);
                    this.showTimePicker = false;
                },
                async syncName() {
                    await this.$wire.set('name', this.localName);
                },
                async syncEmail() {
                    await this.$wire.set('email', this.localEmail);
                },
                async updatePeople(val) {
                    this.localPeople = val;
                    await this.$wire.set('peopleCount', val);
                }
            }));
        });
    </script>

    <nav class="bg-white border-b border-gray-100">
        <div class="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div class="flex h-16 justify-between">
                <div class="flex">
                    <div class="flex shrink-0 items-center">
                        <a href="{{ route('dashboard') }}" class="block text-2xl font-bold tracking-tight text-gray-800">
	                        EVO<span class="text-blue-500">BOTICS</span>
                        </a>
                    </div>
                </div>
                @auth
                    <div class="hidden sm:ms-6 sm:flex sm:items-center sm:gap-2">
                        <x-language-switcher :current="app()->getLocale()" />

                        <div class="relative ms-3" x-data="{ open: false }">
                            <span class="inline-flex rounded-md">
                                <button @click="open = !open" type="button"
                                        class="inline-flex items-center rounded-md border border-transparent bg-white px-3 py-2 text-sm font-medium leading-4 text-gray-500 transition duration-150 ease-in-out hover:text-gray-700 focus:outline-none">
                                    {{ auth()->user()->name }}
                                    <svg class="-me-0.5 ms-2 h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd"/>
                                    </svg>
                                </button>
                            </span>
                            <div x-show="open" @click.away="open = false"
                                 class="absolute right-0 z-50 mt-2 w-48 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 py-1">
                                <a href="{{ route('profile.edit') }}"
                                   class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">{{ __('Profile') }}</a>
                                <form method="POST" action="{{ route('logout') }}">
                                    @csrf
                                    <button type="submit" class="w-full text-left block px-4 py-2 text-sm text-gray-700 hover:bg-gray-100">{{ __('Log Out') }}</button>
                                </form>
                            </div>
                        </div>
                    </div>
                @else
                    <div class="hidden sm:flex sm:items-center sm:gap-2">
                        <x-language-switcher :current="app()->getLocale()" />
                        <a href="{{ route('login') }}"
                           class="inline-flex items-center px-1 pt-1 text-sm font-medium leading-5 text-gray-500 transition duration-150 ease-in-out hover:text-gray-700 focus:outline-none">
                            {{ __('Log in') }}
                        </a>
                    </div>
                @endauth
            </div>
        </div>
    </nav>

    <header class="relative bg-white shadow-sm">
        <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <div class="flex items-center gap-4">
                <a href="{{ route('dashboard') }}" class="text-gray-400 hover:text-gray-600 transition">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="size-6">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18" />
                    </svg>
                </a>
                <h1 class="text-3xl font-bold tracking-tight text-gray-900">{{ __('Booking platform') }}</h1>
            </div>
        </div>
    </header>

    <main>
        <div class="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <div class="grid grid-cols-1 gap-8 lg:grid-cols-3"
                 x-data="reservationForm">

            @if($step === 'form')

                <div class="lg:col-span-2">
                    <h2 class="mb-4 text-xl font-bold">{{ __('1. Pick a date') }}</h2>
                    <div class="overflow-hidden rounded-lg bg-white p-6 shadow-sm sm:rounded-lg">
                        <div class="mb-4 flex items-center justify-between">
                            <button @click="prevMonth()" class="rounded p-2 text-xl hover:bg-gray-100">&larr;</button>
                            <span class="text-lg font-semibold capitalize" x-text="monthName + ' ' + year"></span>
                            <button @click="nextMonth()" class="rounded p-2 text-xl hover:bg-gray-100">&rarr;</button>
                        </div>

                        <div class="grid grid-cols-7 gap-1 text-center text-sm font-medium text-gray-500">
                            <template x-for="day in ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']" :key="day">
                                <div class="py-1" x-text="t[day] || day"></div>
                            </template>
                        </div>

                        <div class="mt-1 grid grid-cols-7 gap-1 text-center">
                            <template x-for="blank in firstDay" :key="'b' + blank">
                                <div></div>
                            </template>
                            <template x-for="day in daysInMonth" :key="day">
                                <button @click="selectDate(day)"
                                        :disabled="isPast(day)"
                                        :class="{
                                            'bg-blue-600 text-white': localDate === `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`,
                                            'text-gray-300 cursor-not-allowed': isPast(day),
                                            'hover:bg-gray-100': !isPast(day)
                                        }"
                                        class="rounded p-2 text-sm transition"
                                        x-text="day">
                                </button>
                            </template>
                        </div>
                    </div>

                    <div class="mt-6 overflow-hidden rounded-lg bg-white p-6 shadow-sm sm:rounded-lg">
                        <h2 class="mb-4 text-xl font-bold">{{ __('2. Pick a time') }}</h2>
                        <p class="mb-3 text-gray-600" x-show="localStartTime && localEndTime" x-text="localStartTime + ' — ' + localEndTime"></p>
                        <p class="mb-3 text-gray-600" x-show="!localDate">{{ __('Pick start time first') }}</p>
                        <button @click="showTimePicker = true"
                                :disabled="!localDate"
                                :class="localDate ? 'bg-blue-600 hover:bg-blue-700 cursor-pointer' : 'bg-gray-300 cursor-not-allowed'"
                                class="rounded-md px-6 py-3 text-white transition">
                            {{ __('Choose a time slot') }}
                        </button>
                    </div>

                    <div x-show="showTimePicker"
                         @click.away="showTimePicker = false"
                         class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
                         style="display: none;">
                        <div class="w-full max-w-lg rounded-xl bg-white p-6 shadow-2xl">
                            <h2 class="mb-4 text-xl font-bold">{{ __('Choose your time slot') }}</h2>
                            <div class="grid grid-cols-2 gap-6">
                                <div>
                                    <p class="mb-2 text-sm font-semibold text-gray-500">{{ __('Start') }}</p>
                                    <div class="space-y-1">
                                        <template x-for="hour in Array.from({length: 11}, (_, i) => i + 9)" :key="'s'+hour">
                                            <button @click="selectStartTime(hour)"
                                                    :class="localStartTime === String(hour).padStart(2, '0') + ':00' ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-gray-200'"
                                                    class="w-full rounded-lg px-4 py-2 text-center font-medium transition">
                                                <span x-text="String(hour).padStart(2, '0') + ':00'"></span>
                                            </button>
                                        </template>
                                    </div>
                                </div>
                                <div>
                                    <p class="mb-2 text-sm font-semibold text-gray-500">{{ __('End') }}</p>
                                    <div class="space-y-1">
                                        <template x-if="!localStartTime">
                                            <p class="text-sm text-gray-400">{{ __('Pick start time first') }}</p>
                                        </template>
                                        <template x-for="hour in endTimeOptions" :key="'e'+hour">
                                            <button @click="selectEndTime(hour)"
                                                    :class="localEndTime === String(hour).padStart(2, '0') + ':00' ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-gray-200'"
                                                    class="w-full rounded-lg px-4 py-2 text-center font-medium transition">
                                                <span x-text="String(hour).padStart(2, '0') + ':00'"></span>
                                            </button>
                                        </template>
                                    </div>
                                </div>
                            </div>
                            <button @click="showTimePicker = false"
                                    class="mt-4 w-full rounded-lg bg-gray-200 px-4 py-2 text-gray-700 hover:bg-gray-300">
                                {{ __('Close') }}
                            </button>
                        </div>
                    </div>
                </div>

                <div class="space-y-6">
                    <div class="overflow-hidden rounded-lg bg-white p-6 shadow-sm sm:rounded-lg">
                        <h2 class="mb-4 text-xl font-bold">{{ __('Your information') }}</h2>
                        <div class="space-y-4">
                            <div>
                                <label class="block text-sm font-medium text-gray-700">{{ __('Name') }}</label>
                                <input type="text" x-model="localName" @input="syncName(); nameError = ''"
                                       class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                                       :class="nameError ? 'border-red-500' : ''">
                                <p x-show="nameError" x-text="nameError" class="mt-1 text-sm text-red-600"></p>
                            </div>
                            <div>
                                <label class="block text-sm font-medium text-gray-700">{{ __('Email') }}</label>
                                <input type="email" x-model="localEmail" @input="syncEmail(); emailError = ''"
                                       class="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"
                                       :class="emailError ? 'border-red-500' : ''">
                                <p x-show="emailError" x-text="emailError" class="mt-1 text-sm text-red-600"></p>
                            </div>
                        </div>
                    </div>

                    <div class="overflow-hidden rounded-lg bg-white p-6 shadow-sm sm:rounded-lg">
                        <h2 class="mb-4 text-xl font-bold">{{ __('Summary') }}</h2>
                        <div class="space-y-3">
                            <div>
                                <span class="text-sm text-gray-500">{{ __('Name') }}</span>
                                <p class="text-lg font-semibold" x-text="localName || '-'"></p>
                            </div>
                            <div>
                                <span class="text-sm text-gray-500">{{ __('Email') }}</span>
                                <p class="text-lg font-semibold" x-text="localEmail || '-'"></p>
                            </div>
                            <div>
                                <span class="text-sm text-gray-500">{{ __('Date') }}</span>
                                <p class="text-lg font-semibold" x-text="formattedDate"></p>
                            </div>
                            <div>
                                <span class="text-sm text-gray-500">{{ __('Time') }}</span>
                                <p class="text-lg font-semibold" x-text="localStartTime && localEndTime ? localStartTime + ' — ' + localEndTime : '-'"></p>
                            </div>
                            <div>
                                <span class="text-sm text-gray-500">{{ __('Guests') }}</span>
                                <p class="text-lg font-semibold" x-text="localPeople"></p>
                            </div>
                        </div>
                    </div>

                    <div class="overflow-hidden rounded-lg bg-white p-6 shadow-sm sm:rounded-lg">
                        <h2 class="mb-4 text-xl font-bold">{{ __('Number of guests (max 30)') }}</h2>
                        <input type="number" x-model="localPeople" @input="updatePeople(localPeople)"
                               min="1" max="30"
                               class="block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm">
                    </div>

                    <button @click="book()"
                            :disabled="!localName || !localEmail || !localDate || !localStartTime || !localEndTime"
                            :class="localName && localEmail && localDate && localStartTime && localEndTime ? 'bg-blue-600 hover:bg-blue-700 cursor-pointer' : 'bg-gray-300 cursor-not-allowed'"
                            class="w-full rounded-md px-4 py-4 text-xl font-bold text-white transition">
                        {{ __('Book now') }}
                    </button>
                </div>
            </div>

            @elseif($step === 'checking')

            <div class="lg:col-span-3 flex flex-col items-center justify-center py-32">
                <svg class="size-20 animate-spin text-blue-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <h2 class="mt-6 text-2xl font-semibold text-gray-900">{{ __('Checking availability...') }}</h2>
                <p class="mt-2 text-gray-500">{{ __('We are looking for an available room, please wait.') }}</p>
            </div>

            @elseif($step === 'result')

            <div class="lg:col-span-3 flex flex-col items-center justify-center py-32">
                @if($roomFound)
                    <svg class="size-24 text-green-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                @else
                    <svg class="size-24 text-red-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 11-18 0 9 9 0 0118 0zm-9 3.75h.008v.008H12v-.008z" />
                    </svg>
                @endif

                <h2 class="mt-6 text-2xl font-semibold {{ $roomFound ? 'text-green-700' : 'text-red-700' }}">
                    {{ $roomFound ? __('Room found!') : __('No room available') }}
                </h2>
                <p class="mt-2 max-w-md text-center text-gray-600">{{ $resultMessage }}</p>

                <button wire:click="resetForm"
                        class="mt-8 rounded-md bg-blue-600 px-8 py-3 text-lg font-semibold text-white hover:bg-blue-700 transition">
                    {{ __('Make another reservation') }}
                </button>
            </div>

            @endif
        </div>
    </main>
</div>

