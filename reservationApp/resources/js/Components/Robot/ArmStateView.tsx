import type { ArmJoints } from './types';

type Props = {
    joints: ArmJoints | null;
};

const JOINTS: Array<{ key: keyof Omit<ArmJoints, 'time'>; label: string; min: number; max: number }> = [
    { key: 'joint1', label: 'Base yaw', min: 0, max: 180 },
    { key: 'joint2', label: 'Shoulder', min: 0, max: 180 },
    { key: 'joint3', label: 'Elbow', min: 0, max: 180 },
    { key: 'joint4', label: 'Wrist pitch', min: 0, max: 180 },
    { key: 'joint5', label: 'Wrist roll', min: 0, max: 180 },
    { key: 'joint6', label: 'Gripper', min: 20, max: 150 },
];

export default function ArmStateView({ joints }: Props) {
    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div>
                <h3 className="text-sm font-semibold text-gray-900">Arm Position</h3>
                <p className="text-xs text-gray-500">Live joint angles from /joint_states</p>
            </div>

            <div className="mt-4 space-y-3">
                {joints ? (
                    JOINTS.map((joint) => {
                        const value = joints[joint.key];
                        const percent = Math.max(0, Math.min(100, ((value - joint.min) / (joint.max - joint.min)) * 100));
                        return (
                            <div className="grid grid-cols-[90px_minmax(0,1fr)_44px] items-center gap-3 text-xs font-semibold text-gray-600" key={joint.key}>
                                <span>{joint.label}</span>
                                <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
                                    <div className="h-full rounded-full bg-blue-500" style={{ width: `${percent}%` }} />
                                </div>
                                <span className="text-right font-mono text-xs text-gray-900">{value} deg</span>
                            </div>
                        );
                    })
                ) : (
                    <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">Waiting for /joint_states</p>
                )}
            </div>
        </section>
    );
}
