import { useEffect, useMemo, useRef, useState } from 'react';
import type { ArmJoints, RosApi } from './types';

type Props = {
    currentJoints: ArmJoints | null;
    ros: RosApi;
};

type JointConfig = {
    key: keyof Omit<ArmJoints, 'time'>;
    label: string;
    min: number;
    max: number;
};

const JOINTS: JointConfig[] = [
    { key: 'joint1', label: 'Base yaw', min: 0, max: 180 },
    { key: 'joint2', label: 'Shoulder', min: 0, max: 180 },
    { key: 'joint3', label: 'Elbow', min: 0, max: 180 },
    { key: 'joint4', label: 'Wrist pitch', min: 0, max: 180 },
    { key: 'joint5', label: 'Wrist roll', min: 0, max: 180 },
    { key: 'joint6', label: 'Gripper', min: 20, max: 150 },
];

const HOME: ArmJoints = { joint1: 90, joint2: 120, joint3: 10, joint4: 20, joint5: 90, joint6: 30, time: 900 };

const PRESETS: Record<string, ArmJoints> = {
    Home: HOME,
    Center: { joint1: 90, joint2: 90, joint3: 90, joint4: 90, joint5: 90, joint6: 90, time: 1000 },
    Camera: { joint1: 90, joint2: 140, joint3: 30, joint4: 40, joint5: 90, joint6: 30, time: 1200 },
    Present: { joint1: 90, joint2: 100, joint3: 70, joint4: 80, joint5: 90, joint6: 30, time: 1200 },
    Open: { ...HOME, joint6: 30, time: 700 },
    Close: { ...HOME, joint6: 90, time: 700 },
};

const clampJoint = (value: number, joint: JointConfig) => Math.max(joint.min, Math.min(joint.max, Math.round(value)));

export default function ArmControlPanel({ currentJoints, ros }: Props) {
    const [enabled, setEnabled] = useState(false);
    const [draft, setDraft] = useState<ArmJoints>(HOME);
    const sendTimerRef = useRef<number | null>(null);

    useEffect(() => {
        if (!enabled && currentJoints) {
            setDraft(currentJoints);
        }
    }, [currentJoints, enabled]);

    const sanitizedDraft = useMemo(() => {
        const next = { ...draft, time: Math.max(100, Math.min(3000, Math.round(draft.time))) };
        JOINTS.forEach((joint) => {
            next[joint.key] = clampJoint(Number(next[joint.key]), joint);
        });
        return next;
    }, [draft]);

    const publishArm = (message: ArmJoints, reason = 'Arm command') => {
        if (!enabled) {
            ros.addLog('Arm command ignored because arm control is locked.', 'warn');
            return;
        }
        ros.publish('/arm6_joints', 'arm_msgs/msg/ArmJoints', message);
        ros.addLog(`${reason}: [${JOINTS.map((joint) => message[joint.key]).join(', ')}]`, 'ok');
    };

    const schedulePublish = (next: ArmJoints) => {
        if (!enabled) return;
        if (sendTimerRef.current) {
            window.clearTimeout(sendTimerRef.current);
        }
        sendTimerRef.current = window.setTimeout(() => publishArm(next, 'Arm slider'), 120);
    };

    const updateJoint = (joint: JointConfig, value: number) => {
        setDraft((current) => {
            const next = { ...current, [joint.key]: clampJoint(value, joint) };
            schedulePublish(next);
            return next;
        });
    };

    const applyPreset = (name: string) => {
        const preset = PRESETS[name];
        setDraft(preset);
        publishArm(preset, `Arm preset ${name}`);
    };

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Arm Control</h3>
                    <p className="text-xs text-gray-500">Publishes /arm6_joints in servo degrees</p>
                </div>
                <button
                    className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${enabled ? 'bg-amber-100 text-amber-800 hover:bg-amber-200' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                    onClick={() => setEnabled((value) => !value)}
                    type="button"
                >
                    {enabled ? 'Arm Unlocked' : 'Arm Locked'}
                </button>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2">
                {Object.keys(PRESETS).map((name) => (
                    <button
                        className="rounded-lg bg-gray-100 px-2 py-2 text-xs font-semibold text-gray-800 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                        disabled={!enabled}
                        key={name}
                        onClick={() => applyPreset(name)}
                        type="button"
                    >
                        {name}
                    </button>
                ))}
            </div>

            <div className="mt-4 space-y-3">
                {JOINTS.map((joint) => (
                    <label className="grid grid-cols-[90px_minmax(0,1fr)_44px] items-center gap-3 text-xs font-semibold text-gray-600" key={joint.key}>
                        <span>{joint.label}</span>
                        <input
                            className="w-full accent-blue-600 disabled:opacity-50"
                            disabled={!enabled}
                            max={joint.max}
                            min={joint.min}
                            onChange={(event) => updateJoint(joint, Number(event.target.value))}
                            step="1"
                            type="range"
                            value={sanitizedDraft[joint.key]}
                        />
                        <span className="text-right font-mono text-xs text-gray-900">{sanitizedDraft[joint.key]} deg</span>
                    </label>
                ))}
            </div>

            <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                Move time {sanitizedDraft.time} ms
                <input
                    className="mt-2 w-full accent-blue-600 disabled:opacity-50"
                    disabled={!enabled}
                    max="3000"
                    min="100"
                    onChange={(event) => setDraft((current) => ({ ...current, time: Number(event.target.value) }))}
                    step="50"
                    type="range"
                    value={sanitizedDraft.time}
                />
            </label>

            <button
                className="mt-4 w-full rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
                disabled={!enabled}
                onClick={() => publishArm(sanitizedDraft, 'Arm apply')}
                type="button"
            >
                Apply Arm Pose
            </button>
        </section>
    );
}
