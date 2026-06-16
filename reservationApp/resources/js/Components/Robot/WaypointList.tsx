import type { RobotPose, RosApi, Waypoint } from './types';

type Props = {
    onAddCurrentPose: () => void;
    onSendWaypoint: (waypoint: Waypoint) => void;
    pose: RobotPose | null;
    ros: RosApi;
    waypoints: Waypoint[];
};

export default function WaypointList({ onAddCurrentPose, onSendWaypoint, pose, ros, waypoints }: Props) {
    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Waypoints</h3>
                    <p className="text-xs text-gray-500">Saved targets for reception and rooms</p>
                </div>
                <button
                    className="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!pose}
                    onClick={onAddCurrentPose}
                    type="button"
                >
                    Save Pose
                </button>
            </div>

            <div className="mt-4 space-y-2">
                {waypoints.map((waypoint) => (
                    <div className="flex items-center justify-between gap-3 rounded-lg border border-gray-100 bg-gray-50 p-3" key={waypoint.id}>
                        <div>
                            <p className="text-sm font-semibold text-gray-900">{waypoint.name}</p>
                            <p className="text-xs text-gray-500">
                                {waypoint.x.toFixed(2)}, {waypoint.y.toFixed(2)}
                            </p>
                        </div>
                        <button
                            className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                            onClick={() => {
                                onSendWaypoint(waypoint);
                                ros.addLog(`Waypoint goal sent: ${waypoint.name}`, 'ok');
                            }}
                            type="button"
                        >
                            Go
                        </button>
                    </div>
                ))}
            </div>
        </section>
    );
}
