import type { DiagnosticStatus } from './types';

type Props = {
    diagnostics: DiagnosticStatus[];
};

const LEVEL_LABELS: Record<number, string> = {
    0: 'OK',
    1: 'Warn',
    2: 'Error',
    3: 'Stale',
};

const LEVEL_CLASS: Record<number, string> = {
    0: 'bg-emerald-100 text-emerald-800 ring-emerald-200',
    1: 'bg-amber-100 text-amber-800 ring-amber-200',
    2: 'bg-red-100 text-red-800 ring-red-200',
    3: 'bg-gray-100 text-gray-700 ring-gray-200',
};

export default function DiagnosticsPanel({ diagnostics }: Props) {
    const sorted = [...diagnostics].sort((a, b) => b.level - a.level || a.name.localeCompare(b.name)).slice(0, 8);

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div>
                <h3 className="text-sm font-semibold text-gray-900">Diagnostics</h3>
                <p className="text-xs text-gray-500">Highest-severity ROS diagnostics first</p>
            </div>

            <div className="mt-4 space-y-2">
                {sorted.length === 0 ? (
                    <p className="rounded-lg bg-gray-50 p-3 text-sm text-gray-500">Waiting for /diagnostics</p>
                ) : (
                    sorted.map((item) => (
                        <div className="rounded-lg border border-gray-100 bg-gray-50 p-3" key={item.id}>
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <p className="truncate text-sm font-semibold text-gray-900">{item.name}</p>
                                    <p className="mt-1 text-xs text-gray-500">{item.message || 'No message'}</p>
                                </div>
                                <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ring-1 ${LEVEL_CLASS[item.level] ?? LEVEL_CLASS[3]}`}>
                                    {LEVEL_LABELS[item.level] ?? `L${item.level}`}
                                </span>
                            </div>
                            <p className="mt-2 text-xs text-gray-400">{item.updatedAt}</p>
                        </div>
                    ))
                )}
            </div>
        </section>
    );
}
