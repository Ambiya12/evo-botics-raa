<?php

namespace Database\Factories;

use App\Models\Session;
use App\Models\Room;
use Illuminate\Database\Eloquent\Factories\Factory;

/**
 * @extends Factory<Session>
 */
class SessionFactory extends Factory
{
    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'date' => $this->faker->dateTimeBetween('now', '+2 weeks')->format('Y-m-d'),
            'start_at' => $this->faker->randomElement(['09:00', '10:00', '14:00', '15:00']),
            'end_at' => fn (array $attributes) => 
                date('H:i', strtotime($attributes['start_at'] . ' +1 hour')),
        ];
    }
}
