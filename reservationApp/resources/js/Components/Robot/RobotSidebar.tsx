import { Link } from '@inertiajs/react';

type NavItem = {
    routeName: string;
    label: string;
    icon: string;
};

const ITEMS: NavItem[] = [
    { routeName: 'admin.robot.overview', label: 'Overview', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6' },
    { routeName: 'admin.robot.navigation', label: 'Navigation', icon: 'M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7' },
    { routeName: 'admin.robot.teleop', label: 'Teleop', icon: 'M11 5h2m-1 0v14m-7-7h14M5 9l-2 3 2 3m14-6l2 3-2 3' },
    { routeName: 'admin.robot.arm', label: 'Arm', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
    { routeName: 'admin.robot.diagnostics', label: 'Diagnostics', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z' },
    { routeName: 'admin.robot.connection', label: 'Connection', icon: 'M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0' },
];

export default function RobotSidebar() {
    return (
        <aside className="w-full shrink-0 md:w-56">
            <nav className="space-y-1 rounded-lg border border-gray-200 bg-white p-2 shadow-sm">
                {ITEMS.map((item) => {
                    const active = route().current(item.routeName);
                    return (
                        <Link
                            className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${active ? 'bg-blue-50 text-blue-700' : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'}`}
                            href={route(item.routeName)}
                            key={item.routeName}
                        >
                            <svg className="h-5 w-5 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.8} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                            </svg>
                            {item.label}
                        </Link>
                    );
                })}
            </nav>
        </aside>
    );
}
