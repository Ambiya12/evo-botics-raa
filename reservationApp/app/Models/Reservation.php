<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Str;

class Reservation extends Model
{
    use HasFactory;

    protected $fillable = [
        'uuid',
        'customer_name',
        'customer_email',
        'status',
        'attendee_count',
        'validated_at',
        'booking_session_id',
    ];

    protected $casts = [
        'validated_at' => 'datetime',
        'attendee_count' => 'integer',
    ];

    public function bookingSession(): BelongsTo
    {
        return $this->belongsTo(BookingSession::class);
    }

    protected static function booted()
    {
        static::creating(function ($reservation) {
            $reservation->uuid = (string) Str::uuid();
        });
    }
}
