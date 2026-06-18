<?php

namespace App\Mail;

use App\Support\ReservationQrPayload;
use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

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
        public ?string $uuid = null,
    ) {
        $this->qrCodeDataUri = ReservationQrPayload::dataUri(
            ReservationQrPayload::forLegacyReservation(
                $name,
                $email,
                $date,
                $startTime,
                $endTime,
                $people,
                $uuid
            )
        );
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
