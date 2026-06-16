import { useState } from 'react';
import type { RobotPose, RosApi } from './types';

type Props = {
    pose: RobotPose | null;
    ros: RosApi;
};

const quaternionFromYaw = (yaw: number) => ({
    x: 0,
    y: 0,
    z: Math.sin(yaw / 2),
    w: Math.cos(yaw / 2),
});

export default function RobotActionsPanel({ pose, ros }: Props) {
    const [speedLimit, setSpeedLimit] = useState(0.22);
    const [initialPose, setInitialPose] = useState({ x: '0', y: '0', yawDeg: '0' });

    const sendInitialPose = () => {
        const yaw = (Number(initialPose.yawDeg) * Math.PI) / 180;
        ros.publish('/initialpose', 'geometry_msgs/msg/PoseWithCovarianceStamped', {
            header: { frame_id: 'map' },
            pose: {
                pose: {
                    position: { x: Number(initialPose.x), y: Number(initialPose.y), z: 0 },
                    orientation: quaternionFromYaw(yaw),
                },
                covariance: [
                    0.25, 0, 0, 0, 0, 0,
                    0, 0.25, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0,
                    0, 0, 0, 0, 0, 0.0685,
                ],
            },
        });
        ros.addLog(`Initial pose set to ${initialPose.x}, ${initialPose.y}, ${initialPose.yawDeg} deg`, 'ok');
    };

    const useCurrentPose = () => {
        if (!pose) return;
        setInitialPose({
            x: pose.x.toFixed(2),
            y: pose.y.toFixed(2),
            yawDeg: Math.round((pose.yaw * 180) / Math.PI).toString(),
        });
    };

    const cancelNavigation = () => {
        ros.publish('/move_base/cancel', 'action_msgs/msg/GoalInfo', {
            stamp: { sec: 0, nanosec: 0 },
            goal_id: { uuid: Array(16).fill(0) },
        });
        ros.publish('/cmd_vel', 'geometry_msgs/msg/Twist', {
            linear: { x: 0, y: 0, z: 0 },
            angular: { x: 0, y: 0, z: 0 },
        });
        ros.addLog('Navigation cancel requested and /cmd_vel stopped.', 'warn');
    };

    const sendSpeedLimit = () => {
        ros.publish('/speed_limit', 'nav2_msgs/msg/SpeedLimit', {
            percentage: false,
            speed_limit: speedLimit,
        });
        ros.addLog(`Nav2 speed limit set to ${speedLimit.toFixed(2)} m/s`, 'ok');
    };

    const beep = () => {
        ros.publish('/beep', 'std_msgs/msg/UInt16', { data: 1 });
        ros.addLog('Beep requested.', 'info');
    };

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Robot Actions</h3>
                    <p className="text-xs text-gray-500">Nav2 safety, localization, speed, and feedback</p>
                </div>
                <button
                    className="rounded-lg bg-red-50 px-3 py-2 text-xs font-semibold text-red-700 hover:bg-red-100"
                    onClick={cancelNavigation}
                    type="button"
                >
                    Cancel Nav
                </button>
            </div>

            <div className="mt-4 grid gap-3">
                <div className="rounded-lg bg-gray-50 p-3">
                    <div className="grid grid-cols-3 gap-2">
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            X
                            <input
                                className="mt-1 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setInitialPose((current) => ({ ...current, x: event.target.value }))}
                                type="number"
                                value={initialPose.x}
                            />
                        </label>
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Y
                            <input
                                className="mt-1 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setInitialPose((current) => ({ ...current, y: event.target.value }))}
                                type="number"
                                value={initialPose.y}
                            />
                        </label>
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Yaw
                            <input
                                className="mt-1 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setInitialPose((current) => ({ ...current, yawDeg: event.target.value }))}
                                type="number"
                                value={initialPose.yawDeg}
                            />
                        </label>
                    </div>
                    <div className="mt-3 flex gap-2">
                        <button
                            className="flex-1 rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                            disabled={!pose}
                            onClick={useCurrentPose}
                            type="button"
                        >
                            Use Current
                        </button>
                        <button
                            className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                            onClick={sendInitialPose}
                            type="button"
                        >
                            Set Initial Pose
                        </button>
                    </div>
                </div>

                <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                    Nav2 speed limit {speedLimit.toFixed(2)} m/s
                    <input
                        className="mt-2 w-full accent-blue-600"
                        max="0.6"
                        min="0.05"
                        onChange={(event) => setSpeedLimit(Number(event.target.value))}
                        step="0.01"
                        type="range"
                        value={speedLimit}
                    />
                </label>

                <div className="flex gap-2">
                    <button
                        className="flex-1 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                        onClick={sendSpeedLimit}
                        type="button"
                    >
                        Apply Speed
                    </button>
                    <button
                        className="flex-1 rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-200"
                        onClick={beep}
                        type="button"
                    >
                        Beep
                    </button>
                </div>
            </div>
        </section>
    );
}
