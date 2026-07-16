import type { RosLogEntry } from '@/hooks/useRosBridge';

type Props = {
    logs: RosLogEntry[];
    onClear: () => void;
};

const COLORS: Record<RosLogEntry['level'], string> = {
    error: 'text-red-600',
    info: 'text-gray-600',
    ok: 'text-emerald-600',
    warn: 'text-amber-600',
};

export default function RobotLogs({ logs, onClear }: Props) {
    return (
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Robot Logs</h3>
                    <p className="text-xs text-gray-500">Dashboard commands and connection events</p>
                </div>
                <button className="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200" onClick={onClear} type="button">
                    Clear
                </button>
            </div>
            <div className="max-h-72 overflow-y-auto p-4 font-mono text-xs">
                {logs.length === 0 ? (
                    <p className="text-gray-500">No log entries yet.</p>
                ) : (
                    logs.slice().reverse().map((log) => (
                        <div className="grid grid-cols-[70px_1fr] gap-3 py-1" key={log.id}>
                            <span className="text-gray-400">{log.at}</span>
                            <span className={COLORS[log.level]}>{log.message}</span>
                        </div>
                    ))
                )}
            </div>
        </section>
    );
}
