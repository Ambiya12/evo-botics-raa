<!DOCTYPE html>
<html lang="{{ str_replace('_', '-', app()->getLocale()) }}" class="h-full bg-gray-100">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<meta name="csrf-token" content="{{ csrf_token() }}">
	<title>EvoBotics</title>
	@vite(['resources/css/app.css', 'resources/js/app.js'])
	@livewireStyles
	<link rel="preconnect" href="https://fonts.bunny.net">
	<link href="https://fonts.bunny.net/css?family=figtree:400,500,600&display=swap" rel="stylesheet" />
	<style>
        .screen {
            overflow: hidden;
            touch-action: none;
            cursor: none;
            user-select: none;
        }
        [x-cloak] { display: none !important; }
	</style>
	<meta name="csrf-token" content="{{ csrf_token() }}">
</head>
<body class="font-sans antialiased">
{{ $slot }}
@livewireScripts
<script src="{{ asset('js/html5-qrcode.min.js') }}"></script>
</body>
</html>