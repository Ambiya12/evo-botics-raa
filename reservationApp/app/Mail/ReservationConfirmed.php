<?php

namespace App\Mail;

use App\Models\Reservation;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Mail\Mailable;
use Illuminate\Mail\Mailables\Attachment;
use Illuminate\Mail\Mailables\Content;
use Illuminate\Mail\Mailables\Envelope;
use Illuminate\Queue\SerializesModels;
use SimpleSoftwareIO\QrCode\Facades\QrCode;

class ReservationConfirmed extends Mailable
{
    use Queueable, SerializesModels;

    /**
     * Create a new message instance.
     */
    public function __construct(
        public Reservation $reservation,
    ) {
        $payload = json_encode([
            'uuid' => $reservation->uuid,
            'name' => $reservation->customer_name,
            'email' => $reservation->customer_email,
            'date' => $reservation->bookingSession->date->format('Y/m/d'),
            'startTime' => $reservation->bookingSession->start_at,
            'endTime' => $reservation->bookingSession->end_at,
            'people' => $reservation->attendee_count,
        ]);
        $secret = config('app.key');
        $signature = hash_hmac('sha256', $payload, $secret);
        $qrData = json_encode(['payload' => $payload, 'signature' => $signature]);
        $this->qrCodePng = QrCode::format('png')->size(300)->generate($qrData);
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

    public string $qrCodePng;
    
    /**
     * Get the attachments for the message.
     *
     * @return array<int, Attachment>
     */
    public function attachments(): array
    {
        return [
            Attachment::fromData(fn () => $this->qrCodePng, 'qrcode.png')
                ->withMime('image/png'),
        ];
    }
}
