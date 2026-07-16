<?php

namespace Database\Seeders;

use App\Models\Room;
use App\Models\BookingSession;
use Illuminate\Database\Console\Seeds\WithoutModelEvents;
use Illuminate\Database\Seeder;

class BookingSessionSeeder extends Seeder
{
    /**
     * Run the database seeds.
     */
    public function run(): void
    {
        $rooms = Room::all();

        foreach ($rooms as $room) {
            BookingSession::factory(1)->create([
                'room_id' => $room->id,
            ]);
        }
    }
}
