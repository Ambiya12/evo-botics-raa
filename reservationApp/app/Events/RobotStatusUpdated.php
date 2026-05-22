<?php

namespace App\Events;

use Illuminate\Broadcasting\Channel;
use Illuminate\Contracts\Broadcasting\ShouldBroadcastNow;

class RobotStatusUpdated implements ShouldBroadcastNow
{
    public function __construct(public readonly array $payload) {}

    public function broadcastOn(): Channel
    {
        return new Channel('robot-dashboard');
    }

    public function broadcastWith(): array
    {
        return $this->payload;
    }
}
