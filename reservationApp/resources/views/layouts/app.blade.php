<!DOCTYPE html>
<html lang="fr">
<head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>Interface Robot</title>
	@vite(['resources/css/app.css', 'resources/js/app.js'])
	<style>
        .screen {
            overflow: hidden;
            touch-action: none;
            cursor: none;
            user-select: none;
        }
	</style>
</head>
<body>
{{ $slot }}
</body>
</html>