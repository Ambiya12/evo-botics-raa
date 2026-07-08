import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ArmJoints, RosApi } from './types';

type Props = {
    connected: boolean;
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

const REST_POSE: ArmJoints = { joint1: 90, joint2: 120, joint3: 10, joint4: 20, joint5: 90, joint6: 30, time: 900 };
const CAMERA_POSE: ArmJoints = { joint1: 90, joint2: 60, joint3: 45, joint4: 90, joint5: 90, joint6: 30, time: 1200 };
const UP_POSE: ArmJoints = { joint1: 90, joint2: 30, joint3: 60, joint4: 90, joint5: 90, joint6: 30, time: 1200 };
const PRESENT_POSE: ArmJoints = { joint1: 90, joint2: 100, joint3: 70, joint4: 80, joint5: 90, joint6: 30, time: 1200 };

const PRESETS: Record<string, Partial<ArmJoints>> = {
    Rest: REST_POSE,
    Camera: CAMERA_POSE,
    Up: UP_POSE,
    Present: PRESENT_POSE,
    Open: { joint6: 30, time: 700 },
    Close: { joint6: 75, time: 700 },
};

const clampJoint = (value: number, joint: JointConfig) => Math.max(joint.min, Math.min(joint.max, Math.round(value)));

const sanitizeArmJoints = (joints: ArmJoints): ArmJoints => {
    const next = { ...joints, time: Math.max(100, Math.min(3000, Math.round(joints.time))) };
    JOINTS.forEach((joint) => {
        next[joint.key] = clampJoint(Number(next[joint.key]), joint);
    });
    return next;
};

export default function ArmControlPanel({ connected, currentJoints, ros }: Props) {
    const [enabled, setEnabled] = useState(false);
    const [holdEnabled, setHoldEnabled] = useState(false);
    const [draft, setDraft] = useState<ArmJoints>(REST_POSE);
    const lastCommandRef = useRef<ArmJoints>(REST_POSE);
    const hasRouteHeartbeat = currentJoints !== null;

    useEffect(() => {
        if (!enabled && currentJoints) {
            const next = sanitizeArmJoints(currentJoints);
            setDraft(next);
            lastCommandRef.current = next;
        }
    }, [currentJoints, enabled]);

    useEffect(() => {
        if (connected) return;
        setEnabled(false);
        setHoldEnabled(false);
    }, [connected]);

    const sanitizedDraft = useMemo(() => sanitizeArmJoints(draft), [draft]);

    const publishArm = useCallback((message: ArmJoints, reason = 'Arm command', shouldLog = true) => {
        if (!enabled) {
            ros.addLog('Arm command ignored because arm control is locked.', 'warn');
            return false;
        }
        const command = sanitizeArmJoints(message);
        const sent = ros.publish('/evo/arm/command', 'arm_msgs/msg/ArmJoints', command);
        if (sent) {
            lastCommandRef.current = command;
        }
        if (shouldLog) {
            ros.addLog(
                `${reason} ${sent ? 'sent' : 'failed'}: [${JOINTS.map((joint) => command[joint.key]).join(', ')}]`,
                sent ? 'ok' : 'error',
            );
        }
        return sent;
    }, [enabled, ros]);

    const updateJoint = (joint: JointConfig, value: number) => {
        setDraft((current) => {
            return { ...current, [joint.key]: clampJoint(value, joint) };
        });
    };

    const applyPreset = (name: string) => {
        const next = { ...sanitizedDraft, ...PRESETS[name] };
        setDraft(next);
        publishArm(next, `Arm preset ${name}`);
    };

    useEffect(() => {
        if (!enabled || !holdEnabled) return;
        const timer = window.setInterval(() => publishArm(lastCommandRef.current, 'Arm hold', false), 1500);
        return () => window.clearInterval(timer);
    }, [enabled, holdEnabled, publishArm]);

    const toggleEnabled = () => {
        setHoldEnabled(false);
        if (enabled) {
            setEnabled(false);
            ros.addLog('Arm control locked; browser pose hold stopped.', 'info');
            return;
        }

        const next = currentJoints ? sanitizeArmJoints(currentJoints) : REST_POSE;
        setDraft(next);
        lastCommandRef.current = next;
        setEnabled(true);
    };

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Arm Control</h3>
                    <p className="text-xs text-gray-500">Publishes /evo/arm/command in servo degrees</p>
                </div>
                <button
                    className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${enabled ? 'bg-amber-100 text-amber-800 hover:bg-amber-200' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                    disabled={!connected}
                    onClick={toggleEnabled}
                    type="button"
                >
                    {enabled ? 'Lock Arm' : 'Unlock Arm'}
                </button>
            </div>

            {!connected && (
                <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
                    Arm control unavailable: rosbridge is disconnected.
                </p>
            )}

            {connected && !hasRouteHeartbeat && (
                <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-xs font-medium text-amber-800">
                    Arm route not confirmed yet: no /arm6_joints messages have been seen. Start the web relay and MCU route before moving the arm.
                </p>
            )}

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
                onClick={() => {
                    publishArm(sanitizedDraft, 'Arm apply');
                }}
                type="button"
            >
                Apply Draft Pose
            </button>

            <button
                className={`mt-2 w-full rounded-lg px-3 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${holdEnabled ? 'bg-amber-100 text-amber-800 hover:bg-amber-200' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'}`}
                disabled={!enabled}
                onClick={() => setHoldEnabled((value) => !value)}
                type="button"
            >
                {holdEnabled ? 'Stop Pose Hold' : 'Start Pose Hold'}
            </button>
        </section>
    );
}
