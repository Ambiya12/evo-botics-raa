<?php

namespace Database\Factories;

use App\Models\ActivityLog;
use App\Models\Reservation;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<ActivityLog>
 */
class ActivityLogFactory extends Factory
{
    protected $model = ActivityLog::class;
    
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        $events = [
            ['type' => 'reservation_created', 'desc' => 'Nouvelle réservation créée'],
            ['type' => 'reservation_validated', 'desc' => 'QR Code scanné et validé'],
            ['type' => 'reservation_cancelled', 'desc' => 'Réservation annulée par l\'utilisateur'],
        ];

        $event = $this->faker->randomElement($events);

        return [
            'action' => $event['type'],
            'description' => $event['desc'],
            'loggable_id' => $this->faker->numberBetween(1, 10),
            'loggable_type' => Reservation::class,
            'payload' => [
                'ip' => $this->faker->ipv4,
                'user_agent' => $this->faker->userAgent,
                'source' => 'API_Test'
            ],
            'created_at' => $this->faker->dateTimeBetween('-1 week', 'now'),
        ];
    }
}
