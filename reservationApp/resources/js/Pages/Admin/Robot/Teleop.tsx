import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import ManualControls from '@/Components/Robot/ManualControls';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';

const Teleop: LayoutComponent = () => {
    const { ros } = useRobotContext();

    return (
        <>
            <Head title="Robot — Teleop" />
            <div className="max-w-md">
                <ManualControls ros={ros} />
            </div>
        </>
    );
};

Teleop.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Teleop;
