import type { RosStatus } from '@/hooks/useRosBridge';

const STATUS_STYLES: Record<RosStatus, string> = {
    idle: 'bg-gray-100 text-gray-700 ring-gray-200',
    connecting: 'bg-amber-100 text-amber-800 ring-amber-200',
    connected: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    disconnected: 'bg-red-100 text-red-800 ring-red-200',
    error: 'bg-red-100 text-red-800 ring-red-200',
};

type Props = {
    cameraUrl: string;
    lastMessageAt: string | null;
    rosUrl: string;
    status: RosStatus;
};

export default function ConnectionStatus({ cameraUrl, lastMessageAt, rosUrl, status }: Props) {
    return (
        <div className="grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">ROS bridge</p>
                <div className="mt-2 flex items-center justify-between gap-3">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${STATUS_STYLES[status]}`}>
                        {status.toUpperCase()}
                    </span>
                    <span className="truncate text-xs text-gray-500">{rosUrl}</span>
                </div>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Camera stream</p>
                <p className="mt-2 truncate text-sm font-medium text-gray-900">{cameraUrl}</p>
            </div>
            <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Last ROS message</p>
                <p className="mt-2 text-sm font-medium text-gray-900">{lastMessageAt ?? 'Waiting for data'}</p>
            </div>
        </div>
    );
}
