<div x-data="{ open: false }" class="relative">
    <button @click="open = !open" type="button"
            class="flex items-center gap-1 rounded-lg border border-gray-200 bg-white px-2 py-1.5 text-sm hover:bg-gray-50 transition">
        @switch($current)
            @case('fr') 🇫🇷 @break
            @case('id') 🇮🇩 @break
            @case('zh') 🇨🇳 @break
            @default 🇬🇧
        @endswitch
        <svg class="h-3 w-3 text-gray-400" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
        </svg>
    </button>

    <div x-show="open" @click.away="open = false" x-transition
         class="absolute right-0 z-50 mt-1 min-w-[120px] rounded-lg border border-gray-200 bg-white py-1 shadow-lg">
        @foreach(['en' => '🇬🇧 EN', 'fr' => '🇫🇷 FR', 'id' => '🇮🇩 ID', 'zh' => '🇨🇳 CN'] as $code => $label)
            <form method="POST" action="{{ route('locale.switch') }}">
                @csrf
                <input type="hidden" name="locale" value="{{ $code }}">
                <button type="submit"
                        class="flex w-full items-center gap-2 px-3 py-2 text-sm transition hover:bg-gray-100 {{ $current === $code ? 'bg-gray-50 font-medium' : '' }}">
                    {{ $label }}
                </button>
            </form>
        @endforeach
    </div>
</div>
