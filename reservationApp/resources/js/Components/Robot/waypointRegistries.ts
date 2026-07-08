import type { OccupancyGrid, Waypoint } from './types';

export type WaypointMap = 'home' | 'school';

// Keep these values synchronized with evo_navigation/config/*_reception_waypoints.yaml.
const REGISTRIES: Record<WaypointMap, Waypoint[]> = {
    home: [
        { id: 'configured-home-reception', name: 'Reception', x: -0.03, y: 0.83, yaw: -1.74, source: 'configured' },
        { id: 'configured-home-1', name: 'Room 1', x: -0.80, y: 0.35, yaw: -2.64, source: 'configured' },
        { id: 'configured-home-2', name: 'Room 2', x: -0.01, y: 1.08, yaw: 1.55, source: 'configured' },
    ],
    school: [
        { id: 'configured-school-reception', name: 'Reception', x: -1.49, y: -0.79, yaw: 1.01, source: 'configured' },
        { id: 'configured-school-1', name: 'Room 1', x: -6.78, y: -8.43, yaw: -2.36, source: 'configured' },
        { id: 'configured-school-2', name: 'Room 2', x: 2.82, y: -4.63, yaw: -0.73, source: 'configured' },
    ],
};

export const identifyWaypointMap = (map: OccupancyGrid | null): WaypointMap | null => {
    if (!map) return null;

    // school_v1.pgm is 485 x 636 with the metadata below. The deployed Home
    // map is private, so any other loaded deployment map uses the Home registry.
    const isSchool = map.info.width === 485
        && map.info.height === 636
        && Math.abs(map.info.resolution - 0.05) < 0.000001
        && Math.abs(map.info.origin.position.x - (-14.1)) < 0.001
        && Math.abs(map.info.origin.position.y - (-18.7)) < 0.001;

    return isSchool ? 'school' : 'home';
};

export const configuredWaypointsFor = (map: WaypointMap | null): Waypoint[] => (
    map ? REGISTRIES[map] : []
);
