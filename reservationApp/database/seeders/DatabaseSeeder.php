<?php

namespace Database\Seeders;

use App\Models\User;
use App\Models\Reservation;
use App\Models\Room;
use App\Models\BookingSession;
use App\Models\ActivityLog;
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
        // User::factory(10)->create();

        /*User::factory()->create([
            'name' => 'Test User',
            'email' => 'test@example.com',
        ]);*/

        Reservation::factory(10)->create();

        Room::factory(10)->create();

        $rooms = Room::all();

        foreach ($rooms as $room) {
            BookingSession::factory(10)->create([
                'room_id' => $room->id,
            ]);
        }

        ActivityLog::factory(10)->create();
    }
}
