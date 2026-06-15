import type { RosApi } from './types';

type Props = {
    ros: RosApi;
};

const ZERO_TWIST = {
    linear: { x: 0, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: 0 },
};

export default function EmergencyStopButton({ ros }: Props) {
    const stopRobot = () => {
        for (let i = 0; i < 5; i += 1) {
            window.setTimeout(() => {
                ros.publish('/cmd_vel', 'geometry_msgs/msg/Twist', ZERO_TWIST);
            }, i * 80);
        }

        ros.publish('/navigate_to_pose/_action/cancel_goal', 'action_msgs/msg/CancelGoal', {
            goal_info: { goal_id: { uuid: Array(16).fill(0) } },
        });
        ros.addLog('Emergency stop sent: zero velocity and navigation cancel.', 'error');
    };

    return (
        <button
            className="inline-flex min-h-11 items-center justify-center rounded-lg bg-red-600 px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
            onClick={stopRobot}
            type="button"
        >
            Emergency Stop
        </button>
    );
}
