import { useEffect, useState } from 'react';
import type { TopicHeartbeat } from './types';

type Props = {
    topics: TopicHeartbeat[];
};

const ageLabel = (lastSeenAt: number | null, now: number) => {
    if (!lastSeenAt) return 'Waiting';
    const ageSeconds = Math.max(0, Math.round((now - lastSeenAt) / 1000));
    if (ageSeconds < 2) return 'Live';
    return `${ageSeconds}s ago`;
};

const statusClass = (lastSeenAt: number | null, now: number) => {
    if (!lastSeenAt) return 'bg-gray-100 text-gray-700 ring-gray-200';
    const ageSeconds = (now - lastSeenAt) / 1000;
    if (ageSeconds < 3) return 'bg-emerald-100 text-emerald-800 ring-emerald-200';
    if (ageSeconds < 10) return 'bg-amber-100 text-amber-800 ring-amber-200';
    return 'bg-red-100 text-red-800 ring-red-200';
};

export default function SensorStatusPanel({ topics }: Props) {
    const [now, setNow] = useState(Date.now());

    useEffect(() => {
        const timer = window.setInterval(() => setNow(Date.now()), 1000);
        return () => window.clearInterval(timer);
    }, []);

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div>
                <h3 className="text-sm font-semibold text-gray-900">Sensor Status</h3>
                <p className="text-xs text-gray-500">Topic heartbeat from rosbridge subscriptions</p>
            </div>

            <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {topics.map((topic) => (
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3" key={topic.key}>
                        <div className="flex items-start justify-between gap-3">
                            <div className="min-w-0">
                                <p className="text-sm font-semibold text-gray-900">{topic.label}</p>
                                <p className="truncate text-xs text-gray-500">{topic.topic}</p>
                            </div>
                            <span className={`shrink-0 rounded-full px-2 py-1 text-xs font-semibold ring-1 ${statusClass(topic.lastSeenAt, now)}`}>
                                {ageLabel(topic.lastSeenAt, now)}
                            </span>
                        </div>
                        <p className="mt-2 text-xs text-gray-500">{topic.messageCount} messages</p>
                    </div>
                ))}
            </div>
        </section>
    );
}
