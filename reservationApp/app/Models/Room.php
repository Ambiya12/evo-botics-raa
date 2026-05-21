<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class Room extends Model
{
    use HasFactory;
    
    protected $fillable = [
        'name',
        'max_capacity',
    ];

    public function sessions()
    {
        return $this->hasMany(BookingSession::class);
    }

    public function hasCapacity($query, int $numberOfPeople)
    {
        return $query->where('max_capacity', '>=', $numberOfPeople);
    }
}
