<x-mail::message>
# Thanks for your reservation, {{ $reservation->customer_name }} !

Your room is reserved for **{{ $reservation->bookingSession->date->format('Y/m/d') }}**.

**Details:**
- Room : {{ $reservation->bookingSession->room->name }}
- Time : {{ $reservation->bookingSession->start_at }} to {{ $reservation->bookingSession->end_at }}
- Number of People : {{ $reservation->attendee_count }}

	<div style="margin-top: 24px; text-align: center;">
		<p style="color: #6b7280; font-size: 14px; margin-bottom: 12px;">Present this QR code at the kiosk to validate your reservation:</p>
		<img src="data:image/png;base64,{{ $qrCode }}" alt="QR Code" style="width: 200px; height: 200px;">
		<p style="color: #9ca3af; font-size: 12px; margin-top: 8px;">If the image does not display, the QR code is also attached as a file.</p>
	</div>
{{--
<x-mail::button :url="config('app.url')">
View my reservation
</x-mail::button>
--}}
See you soon,<br>
{{ config('app.name') }}
</x-mail::message>