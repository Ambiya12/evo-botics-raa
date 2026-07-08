<?php

namespace App\Mail;

use App\Models\Reservation;
use Illuminate\Bus\Queueable;
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
    ) {}

    private function generateQrCode(): string
    {
        $qrData = json_encode([
            'payload' => json_encode($this->reservation->getQrPayload()),
            'signature' => $this->reservation->generateSignature()
        ]);

        return QrCode::format('png')->size(300)->generate($qrData);
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
            with: [
                'validating' => base64_encode($this->generateQrCode()),
            ],
        );
    }
    
    /**
     * Get the attachments for the message.
     *
     * @return array<int, Attachment>
     */
    public function attachments(): array
    {
        return [
            Attachment::fromData(fn () => $this->generateQrCode(), 'qrcode.png')
                ->withMime('image/png'),
        ];
    }
}
