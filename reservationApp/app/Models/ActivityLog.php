<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Str;

class ActivityLog extends Model
{
    use HasFactory;

    protected $fillable = [
        'action',
        'description',
        'loggable_id',
        'loggable_type',
        'payload',
    ];

    protected $casts = [
        'payload' => 'array',
    ];

    public function loggable()
    {
        return $this->morphTo();
    }
}
