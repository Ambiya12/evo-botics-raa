import EmergencyStopButton from './EmergencyStopButton';
import { useRobotContext } from './RobotContext';
import type { RosStatus } from '@/hooks/useRosBridge';

const STATUS_STYLES: Record<RosStatus, string> = {
    idle: 'bg-gray-100 text-gray-700 ring-gray-200',
    connecting: 'bg-amber-100 text-amber-800 ring-amber-200',
    connected: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    disconnected: 'bg-red-100 text-red-800 ring-red-200',
    error: 'bg-red-100 text-red-800 ring-red-200',
};

export default function RobotHeader() {
    const { config, ros, status, rosUrl } = useRobotContext();
    const rosLabel = rosUrl || 'Robot IP not configured';

    return (
        <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
                <h2 className="text-xl font-semibold leading-tight text-gray-800">Robot Admin Dashboard</h2>
                <p className="mt-1 text-sm text-gray-500">General status, navigation, manual control, arm and diagnostics.</p>
            </div>
            <div className="flex items-center gap-3">
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ring-1 ${STATUS_STYLES[status]}`}>
                    {status.toUpperCase()}
                </span>
                <span className="hidden truncate text-xs text-gray-500 sm:inline">{rosLabel}</span>
                <EmergencyStopButton navigationActionName={config.navigationActionName} ros={ros} />
            </div>
        </div>
    );
}
