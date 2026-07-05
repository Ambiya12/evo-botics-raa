<?php

$roomIds = array_filter(
    array_map(
        'intval',
        preg_split('/\s*,\s*/', (string) env('EVO_NAVIGABLE_ROOM_IDS', '1,2'))
    ),
    static fn (int $roomId): bool => $roomId > 0
);

return [
    // Must match the destination IDs in the active robot waypoint registry.
    'navigable_room_ids' => array_values(array_unique($roomIds)),
];
