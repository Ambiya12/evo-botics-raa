<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; padding: 24px;">
    <h1 style="color: #2563eb;">EvoBotics — Reservation Confirmed</h1>
    <p>Hello <strong>{{ $name }}</strong>,</p>
    <p>Your reservation has been confirmed. Here is a summary:</p>

    <table style="width: 100%; max-width: 480px; border-collapse: collapse; margin-top: 16px;">
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Date</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">{{ $date }}</td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Time</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">{{ $startTime }} — {{ $endTime }}</td>
        </tr>
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; color: #6b7280;">Guests</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e5e7eb; font-weight: 600;">{{ $people }}</td>
        </tr>
    </table>

    <div style="margin-top: 24px; text-align: center;">
        <p style="color: #6b7280; font-size: 14px; margin-bottom: 12px;">Present this QR code at the kiosk to validate your reservation:</p>
        <img src="{{ $qrCodeDataUri }}" alt="QR Code" style="width: 200px; height: 200px;">
        <p style="color: #9ca3af; font-size: 12px; margin-top: 8px;">If the image does not display, use the QR code shown on the reservation confirmation page.</p>
    </div>
</body>
</html>
