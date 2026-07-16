import type { ReactNode } from 'react';
import AuthenticatedLayout from '@/Layouts/AuthenticatedLayout';
import RobotHeader from '@/Components/Robot/RobotHeader';
import RobotSidebar from '@/Components/Robot/RobotSidebar';
import { RobotProvider } from '@/Components/Robot/RobotContext';

export default function RobotLayout({ children }: { children: ReactNode }) {
    return (
        <RobotProvider>
            <AuthenticatedLayout header={<RobotHeader />}>
                <div className="mx-auto flex max-w-7xl flex-col gap-6 px-4 py-6 sm:px-6 md:flex-row lg:px-8">
                    <RobotSidebar />
                    <main className="min-w-0 flex-1 space-y-6">{children}</main>
                </div>
            </AuthenticatedLayout>
        </RobotProvider>
    );
}
