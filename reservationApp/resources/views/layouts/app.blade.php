<!DOCTYPE html>
<html lang="fr" class="h-full bg-gray-100">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Interface Robot</title>
	@vite(['resources/css/app.css', 'resources/js/app.js'])
	@livewireStyles
	<style>
        .screen {
            overflow: hidden;
            touch-action: none;
            cursor: none;
            user-select: none;
        }
	</style>
</head>
<body class="h-full">
{{ $slot }}
@livewireScripts
</body>
</html>