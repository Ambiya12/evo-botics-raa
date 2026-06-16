import type { BatteryState, RobotPose } from './types';

type Props = {
    battery: BatteryState | null;
    diagnosticsLevel: number | null;
    mapSize: string;
    pose: RobotPose | null;
};

const DIAGNOSTIC_LABELS: Record<number, string> = {
    0: 'OK',
    1: 'Warning',
    2: 'Error',
    3: 'Stale',
};

const diagnosticTone = (level: number | null) => {
    if (level === null) return 'text-gray-900';
    if (level === 0) return 'text-emerald-700';
    if (level === 1) return 'text-amber-700';
    return 'text-red-700';
};

const batteryTone = (battery: BatteryState | null) => {
    if (!battery) return 'text-gray-900';
    if (battery.level === 'good') return 'text-emerald-700';
    if (battery.level === 'low') return 'text-amber-700';
    if (battery.level === 'critical') return 'text-red-700';
    return 'text-gray-900';
};

export default function RobotHealthCards({ battery, diagnosticsLevel, mapSize, pose }: Props) {
    const cards = [
        {
            label: 'Battery',
            value: battery?.displayValue ?? 'Waiting',
            detail: battery?.estimateLabel,
            tone: batteryTone(battery),
        },
        {
            label: 'Position',
            value: pose ? `${pose.x.toFixed(2)}, ${pose.y.toFixed(2)}` : 'Waiting',
        },
        {
            label: 'Heading',
            value: pose ? `${Math.round((pose.yaw * 180) / Math.PI)} deg` : 'Waiting',
        },
        {
            label: 'Speed',
            value: pose ? `${pose.linearSpeed.toFixed(2)} m/s` : 'Waiting',
        },
        {
            label: 'Angular',
            value: pose ? `${pose.angularSpeed.toFixed(2)} rad/s` : 'Waiting',
        },
        {
            label: 'Map',
            value: mapSize || 'Waiting',
        },
        {
            label: 'Diagnostics',
            value: diagnosticsLevel === null ? 'Waiting' : DIAGNOSTIC_LABELS[diagnosticsLevel] ?? `Level ${diagnosticsLevel}`,
            tone: diagnosticTone(diagnosticsLevel),
        },
    ];

    return (
        <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-7">
            {cards.map((card) => (
                <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm" key={card.label}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">{card.label}</p>
                    <p className={`mt-2 text-lg font-semibold ${card.tone ?? 'text-gray-900'}`}>{card.value}</p>
                    {card.detail ? <p className="mt-1 text-xs text-gray-500">{card.detail}</p> : null}
                </div>
            ))}
        </section>
    );
}
