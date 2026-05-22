<x-mail::message>
# Thanks for your reservation, {{ $reservation->customer_name }} !

Your room is reserved for **{{ $reservation->bookingSession->date->format('Y/m/d') }}**.

**Details:**
- Room : {{ $reservation->bookingSession->room->name }}
- Time : {{ $reservation->bookingSession->start_at }} à {{ $reservation->bookingSession->end_at }}
- Number of People : {{ $reservation->attendee_count }}


{{--
<x-mail::button :url="config('app.url')">
View my reservation
</x-mail::button>
--}}
See you soon,<br>
{{ config('app.name') }}
</x-mail::message>