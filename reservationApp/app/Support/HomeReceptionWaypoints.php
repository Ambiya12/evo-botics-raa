<?php

namespace App\Support;

use Symfony\Component\Yaml\Yaml;

class HomeReceptionWaypoints
{
    /**
     * @return array<int, array{id: string, name: string, x: float, y: float, yaw: float, predefined: true}>
     */
    public static function load(?string $path = null): array
    {
        $path ??= base_path('../evo_ws/src/evo_navigation/config/home_reception_waypoints.yaml');

        if (! is_file($path)) {
            return [];
        }

        $waypoints = Yaml::parseFile($path)['waypoints'] ?? [];

        if (! is_array($waypoints)) {
            return [];
        }

        $result = [];
        foreach ($waypoints as $id => $pose) {
            if (
                ! is_array($pose)
                || ! is_numeric($pose['x'] ?? null)
                || ! is_numeric($pose['y'] ?? null)
                || ! is_numeric($pose['yaw'] ?? null)
            ) {
                continue;
            }

            $key = (string) $id;
            $result[] = [
                'id' => "predefined-{$key}",
                'name' => $key === 'reception' ? 'Reception' : "Room {$key}",
                'x' => (float) $pose['x'],
                'y' => (float) $pose['y'],
                // The ROS registry stores yaw in radians. The UI converts it for display.
                'yaw' => (float) $pose['yaw'],
                'predefined' => true,
            ];
        }

        return $result;
    }
}
