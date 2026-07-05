import { useEffect, useMemo, useState } from 'react';
import type { RosApi } from './types';

type Props = {
    connected: boolean;
    ros: RosApi;
};

const KEYS = ['w', 'a', 's', 'd', 'ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight', ' '] as const;

export default function ManualControls({ connected, ros }: Props) {
    const [speed, setSpeed] = useState(0.16);
    const [turnSpeed, setTurnSpeed] = useState(0.7);
    const [teleopEnabled, setTeleopEnabled] = useState(false);
    const [pressed, setPressed] = useState<Record<string, boolean>>({});
    const [buttonCommand, setButtonCommand] = useState<{ angularZ: number; linearX: number } | null>(null);

    const twist = useMemo(() => {
        let linearX = 0;
        let angularZ = 0;

        if (buttonCommand) {
            linearX = buttonCommand.linearX;
            angularZ = buttonCommand.angularZ;
        } else {
            if (pressed.w || pressed.ArrowUp) linearX += speed;
            if (pressed.s || pressed.ArrowDown) linearX -= speed;
            if (pressed.a || pressed.ArrowLeft) angularZ += turnSpeed;
            if (pressed.d || pressed.ArrowRight) angularZ -= turnSpeed;
        }

        if (pressed[' ']) {
            linearX = 0;
            angularZ = 0;
        }

        return {
            linear: { x: linearX, y: 0, z: 0 },
            angular: { x: 0, y: 0, z: angularZ },
        };
    }, [buttonCommand, pressed, speed, turnSpeed]);

    const sendTwist = (linearX: number, angularZ: number) => {
        ros.publish('/cmd_vel_teleop', 'geometry_msgs/msg/Twist', {
            linear: { x: linearX, y: 0, z: 0 },
            angular: { x: 0, y: 0, z: angularZ },
        });
    };

    const stop = () => sendTwist(0, 0);

    const startButtonCommand = (linearX: number, angularZ: number) => {
        setButtonCommand({ linearX, angularZ });
        sendTwist(linearX, angularZ);
    };

    const stopButtonCommand = () => {
        setButtonCommand(null);
        stop();
    };

    useEffect(() => {
        if (connected) return;
        setTeleopEnabled(false);
        setPressed({});
        setButtonCommand(null);
    }, [connected]);

    useEffect(() => {
        if (!teleopEnabled && !buttonCommand) {
            return;
        }

        const timer = window.setInterval(() => {
            ros.publish('/cmd_vel_teleop', 'geometry_msgs/msg/Twist', twist);
        }, 120);

        return () => window.clearInterval(timer);
    }, [buttonCommand, ros, teleopEnabled, twist]);

    useEffect(() => {
        const onKeyDown = (event: KeyboardEvent) => {
            if (!teleopEnabled) return;
            if ((KEYS as readonly string[]).includes(event.key)) {
                event.preventDefault();
                setPressed((current) => ({ ...current, [event.key]: true }));
            }
            if (event.key === 'Escape') {
                setTeleopEnabled(false);
                setPressed({});
                stop();
            }
        };

        const onKeyUp = (event: KeyboardEvent) => {
            if ((KEYS as readonly string[]).includes(event.key)) {
                setPressed((current) => ({ ...current, [event.key]: false }));
            }
        };

        window.addEventListener('keydown', onKeyDown);
        window.addEventListener('keyup', onKeyUp);
        window.addEventListener('blur', stop);

        return () => {
            window.removeEventListener('keydown', onKeyDown);
            window.removeEventListener('keyup', onKeyUp);
            window.removeEventListener('blur', stop);
        };
    });

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Manual Control</h3>
                    <p className="text-xs text-gray-500">Hold buttons or enable keyboard teleop</p>
                </div>
                <button
                    className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${teleopEnabled ? 'bg-amber-100 text-amber-800' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                    disabled={!connected}
                    onClick={() => {
                        setTeleopEnabled((value) => !value);
                        setPressed({});
                        setButtonCommand(null);
                        stop();
                    }}
                    type="button"
                >
                    {teleopEnabled ? 'Keyboard On' : 'Keyboard Off'}
                </button>
            </div>

            {!connected && (
                <p className="mt-4 rounded-lg bg-red-50 px-3 py-2 text-xs font-medium text-red-700">
                    Manual control unavailable: rosbridge is disconnected.
                </p>
            )}

            <div className="mt-4 grid grid-cols-3 gap-2">
                <div />
                <DriveButton disabled={!connected} label="Forward" onPress={() => startButtonCommand(speed, 0)} onRelease={stopButtonCommand} />
                <div />
                <DriveButton disabled={!connected} label="Left" onPress={() => startButtonCommand(0, turnSpeed)} onRelease={stopButtonCommand} />
                <DriveButton disabled={!connected} label="Stop" onPress={stopButtonCommand} onRelease={stopButtonCommand} tone="danger" />
                <DriveButton disabled={!connected} label="Right" onPress={() => startButtonCommand(0, -turnSpeed)} onRelease={stopButtonCommand} />
                <div />
                <DriveButton disabled={!connected} label="Back" onPress={() => startButtonCommand(-speed, 0)} onRelease={stopButtonCommand} />
                <div />
            </div>

            <label className="mt-5 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                Linear speed {speed.toFixed(2)} m/s
                <input
                    className="mt-2 w-full accent-blue-600"
                    max="0.28"
                    min="0.05"
                    onChange={(event) => setSpeed(Number(event.target.value))}
                    step="0.01"
                    type="range"
                    value={speed}
                />
            </label>
            <label className="mt-4 block text-xs font-semibold uppercase tracking-wide text-gray-500">
                Turn speed {turnSpeed.toFixed(2)} rad/s
                <input
                    className="mt-2 w-full accent-blue-600"
                    max="1.0"
                    min="0.2"
                    onChange={(event) => setTurnSpeed(Number(event.target.value))}
                    step="0.05"
                    type="range"
                    value={turnSpeed}
                />
            </label>
            <p className="mt-3 text-xs text-gray-500">
                Keyboard: W/A/S/D or arrows, space to stop, escape to exit. A sent command confirms rosbridge delivery only, not wheel motion.
            </p>
        </section>
    );
}

function DriveButton({
    disabled,
    label,
    onPress,
    onRelease,
    tone = 'default',
}: {
    disabled: boolean;
    label: string;
    onPress: () => void;
    onRelease: () => void;
    tone?: 'default' | 'danger';
}) {
    return (
        <button
            className={`min-h-12 touch-none select-none rounded-lg px-3 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${tone === 'danger' ? 'bg-red-50 text-red-700 hover:bg-red-100' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'}`}
            disabled={disabled}
            onPointerCancel={onRelease}
            onPointerDown={(event) => {
                event.currentTarget.setPointerCapture(event.pointerId);
                onPress();
            }}
            onPointerUp={onRelease}
            type="button"
        >
            {label}
        </button>
    );
}
