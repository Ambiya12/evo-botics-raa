<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class Reservation extends Model
{
    use HasFactory;

    protected $fillable = [
        'uuid',
        'customer_name',
        'customer_email',
        'reservation_date',
        'status',
        'validated_at',
    ];

    protected static function booted()
    {
        static::creating(function ($reservation) {
            $reservation->uuid = (string) Str::uuid();
        });
    }

    protected $casts = [
        'reservation_date' => 'datetime',
        'validated_at' => 'datetime',
    ];
}
