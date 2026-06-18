<x-mail::message>
# Thanks for your reservation, {{ $reservation->customer_name }} !

Your room is reserved for **{{ $reservation->bookingSession->date->format('Y/m/d') }}**.

**Details:**
- Room : {{ $reservation->bookingSession->room->name }}
- Time : {{ $reservation->bookingSession->start_at }} to {{ $reservation->bookingSession->end_at }}
- Number of People : {{ $reservation->attendee_count }}

<div style="text-align: center; margin: 24px 0;">
    <p>Present this QR code to the robot kiosk when you arrive:</p>
    <img src="{{ $qrCodeDataUri }}" alt="Reservation QR Code" width="220" height="220">
</div>

{{--
<x-mail::button :url="config('app.url')">
View my reservation
</x-mail::button>
--}}
See you soon,<br>
{{ config('app.name') }}
</x-mail::message>
