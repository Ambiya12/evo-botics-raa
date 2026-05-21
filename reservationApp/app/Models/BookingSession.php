<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Support\Str;

class BookingSession extends Model
{
    use HasFactory;
    
    protected $fillable = [
        'room_id',
        'date',
        'start_at',
        'end_at',
        'is_available',
    ];

    protected $casts = [
        'date' => 'date',
        'is_available' => 'boolean',
    ];

    public function room() : BelongsTo
    {
        return $this->belongsTo(Room::class);
    }
}
