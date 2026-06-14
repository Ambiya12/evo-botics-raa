<?php

namespace Database\Factories;

use App\Models\Reservation;
use App\Models\User;
use App\Models\BookingSession;
use Illuminate\Database\Eloquent\Factories\Factory;
use Illuminate\Support\Str;

/**
 * @extends Factory<Reservation>
 */
class ReservationFactory extends Factory
{
    protected $model = Reservation::class;

    /**
     * Define the model's default state.
     *
     * @return array<string, mixed>
     */
    public function definition(): array
    {
        return [
            'uuid' => (string) Str::uuid(),
            'customer_name' => $this->faker->name(),
            'customer_email' => $this->faker->unique()->safeEmail(),
            'status' => $this->faker->randomElement(['pending', 'validated', 'cancelled', 'expired']),
            'attendee_count' => $this->faker->numberBetween(5, 20),
            'validated_at' => function (array $attributes) {
                return $attributes['status'] === 'validated' ? now() : null;
            },
            'user_id' => User::factory(), 
            'booking_session_id' => BookingSession::factory(),
        ];
    }
}
