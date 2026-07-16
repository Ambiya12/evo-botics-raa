<?php

namespace Tests\Unit;

use App\Support\HomeReceptionWaypoints;
use PHPUnit\Framework\TestCase;

class HomeReceptionWaypointsTest extends TestCase
{
    public function test_it_loads_the_home_navigation_targets(): void
    {
        $path = dirname(__DIR__, 3).'/evo_ws/src/evo_navigation/config/home_reception_waypoints.yaml';

        $waypoints = HomeReceptionWaypoints::load($path);

        $this->assertSame(['Reception', 'Room 1', 'Room 2'], array_column($waypoints, 'name'));
        $this->assertSame(['predefined-reception', 'predefined-1', 'predefined-2'], array_column($waypoints, 'id'));
        $this->assertSame([-1.74, -2.64, 1.55], array_column($waypoints, 'yaw'));
        $this->assertSame([true, true, true], array_column($waypoints, 'predefined'));
    }
}
