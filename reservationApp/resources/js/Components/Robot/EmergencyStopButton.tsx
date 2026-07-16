import { useEffect, useState } from 'react';
import type { RosApi } from './types';

type Props = {
    navigationActionName: string;
    ros: RosApi;
};

const ZERO_TWIST = {
    linear: { x: 0, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: 0 },
};

const CANCEL_ALL_GOALS = {
    goal_info: {
        stamp: { sec: 0, nanosec: 0 },
        goal_id: { uuid: Array(16).fill(0) },
    },
};

export default function EmergencyStopButton({ navigationActionName, ros }: Props) {
    const [estopActive, setEstopActive] = useState(false);

    useEffect(() => ros.subscribe('/e_stop_active', (message) => {
        if (typeof message === 'object' && message !== null && 'data' in message) {
            setEstopActive(Boolean((message as { data?: unknown }).data));
        }
    }, { type: 'std_msgs/msg/Bool', throttleRate: 250 }), [ros]);

    const publishZeroCommands = () => {
        ros.publish('/cmd_vel_nav', 'geometry_msgs/msg/Twist', ZERO_TWIST);
        ros.publish('/cmd_vel_nav_raw', 'geometry_msgs/msg/Twist', ZERO_TWIST);
        ros.publish('/cmd_vel_teleop', 'geometry_msgs/msg/Twist', ZERO_TWIST);
        ros.publish('/cmd_vel_selected', 'geometry_msgs/msg/Twist', ZERO_TWIST);
    };

    const stopRobot = () => {
        ros.publish('/e_stop', 'std_msgs/msg/Bool', { data: true });
        ros.publish('/explore/resume', 'std_msgs/msg/Bool', { data: false });
        ros.callService(`${navigationActionName.replace(/\/$/, '')}/_action/cancel_goal`, {
            type: 'action_msgs/srv/CancelGoal',
            args: CANCEL_ALL_GOALS,
        });

        for (let i = 0; i < 5; i += 1) {
            window.setTimeout(() => {
                publishZeroCommands();
            }, i * 80);
        }

        ros.addLog('Emergency stop latched: exploration paused, Nav2 canceled, velocity gated.', 'error');
    };

    const resetStop = () => {
        publishZeroCommands();
        ros.publish('/e_stop_reset', 'std_msgs/msg/Bool', { data: true });
        ros.addLog('Emergency stop reset requested. Verify the robot area is clear before moving.', 'warn');
    };

    return (
        <div className="flex items-center gap-2">
            {estopActive && (
                <button
                    className="inline-flex min-h-11 items-center justify-center rounded-lg bg-amber-100 px-4 py-2.5 text-sm font-bold text-amber-900 shadow-sm transition hover:bg-amber-200 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:ring-offset-2"
                    onClick={resetStop}
                    type="button"
                >
                    Reset Stop
                </button>
            )}
            <button
                className="inline-flex min-h-11 items-center justify-center rounded-lg bg-red-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
                onClick={stopRobot}
                type="button"
            >
                Emergency Stop
            </button>
        </div>
    );
}
