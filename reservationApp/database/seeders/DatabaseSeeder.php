<?php

namespace Database\Seeders;

use App\Models\ActivityLog;
use App\Models\BookingSession;
use App\Models\Reservation;
use App\Models\Room;
use App\Models\User;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    use WithoutModelEvents;

    /**
     * Seed the application's database.
     */
    public function run(): void
    {
        $users = User::factory(10)->create();

        // Dev admin for manual testing (login: admin@example.com / password "password").
        User::factory()->admin()->create([
            'name' => 'Admin Dev',
            'email' => 'admin@example.com',
        ]);

        Room::factory(10)->create();

        $rooms = Room::all();

        foreach ($rooms as $room) {
            BookingSession::factory(10)->create([
                'room_id' => $room->id,
            ]);
        }

        $sessions = BookingSession::all();

        for ($i = 0; $i < 10; $i++) {
            Reservation::factory()->create([
                'user_id' => $users->random()->id,
                'booking_session_id' => $sessions->random()->id,
            ]);
        }

        ActivityLog::factory(10)->create();
    }
}
