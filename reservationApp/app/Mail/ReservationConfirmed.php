<?php

namespace App\Mail;

use App\Models\Reservation;
use App\Support\ReservationQrPayload;
use Illuminate\Bus\Queueable;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Attachment;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;

class ReservationConfirmed extends Mailable
{
    use Queueable, SerializesModels;

    public string $qrCodeDataUri;
    private $qrCodePng;

    /**
     * Create a new message instance.
     */
    public function __construct(
        public Reservation $reservation,
    ) {
        $this->qrCodeDataUri = ReservationQrPayload::dataUri(
            ReservationQrPayload::forReservation($reservation)
        );
    }

    /**
     * Get the message envelope.
     */
    public function envelope(): Envelope
    {
        return new Envelope(
            subject: 'Reservation Confirmed',
        );
    }

    /**
     * Get the message content definition.
     */
    public function content(): Content
    {
        return new Content(
            markdown: 'emails.reservations.confirmed',
        );
    }

    /**
     * Get the attachments for the message.
     *
     * @return array<int, \Illuminate\Mail\Mailables\Attachment>
     */
    public function attachments(): array
    {
        return [
            Attachment::fromData(fn () => $this->qrCodePng, 'qrcode.png')
                ->withMime('image/png'),
        ];
    }
}
