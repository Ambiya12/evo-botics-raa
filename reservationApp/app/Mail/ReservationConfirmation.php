<?php

namespace App\Mail;

use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;
use SimpleSoftwareIO\QrCode\Facades\QrCode;

class ReservationConfirmation extends Mailable
{
    use Queueable, SerializesModels;

    public string $qrCodeDataUri;

    public function __construct(
        public string $name,
        public string $email,
        public string $date,
        public string $startTime,
        public string $endTime,
        public int $people,
    ) {
        $payload = json_encode([
            'name' => $name,
            'email' => $email,
            'date' => $date,
            'startTime' => $startTime,
            'endTime' => $endTime,
            'people' => $people,
        ]);

        $secret = config('app.key');
        $signature = hash_hmac('sha256', $payload, $secret);
        $qrData = json_encode([
            'payload' => $payload,
            'signature' => $signature,
        ]);

        $svg = QrCode::size(300)->generate($qrData);
        $this->qrCodeDataUri = 'data:image/svg+xml;base64,'.base64_encode($svg);
    }

    public function envelope(): Envelope
    {
        return new Envelope(
            subject: 'EvoBotics — Reservation Confirmed',
        );
    }

    public function content(): Content
    {
        return new Content(
            view: 'emails.reservation-confirmation',
        );
    }

    public function attachments(): array
    {
        return [];
    }
}
