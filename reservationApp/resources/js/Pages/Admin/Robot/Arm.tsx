import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import ArmControlPanel from '@/Components/Robot/ArmControlPanel';
import ArmStateView from '@/Components/Robot/ArmStateView';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';

const Arm: LayoutComponent = () => {
    const { ros, status, telemetry } = useRobotContext();

    return (
        <>
            <Head title="Robot — Arm" />
            <div className="grid gap-6 lg:grid-cols-2">
                <ArmControlPanel
                    connected={status === 'connected'}
                    currentJoints={telemetry.armJoints}
                    ros={ros}
                />
                <ArmStateView joints={telemetry.armJoints} />
            </div>
        </>
    );
};

Arm.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Arm;
