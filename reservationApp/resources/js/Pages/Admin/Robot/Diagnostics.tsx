import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import DiagnosticsPanel from '@/Components/Robot/DiagnosticsPanel';
import RobotLogs from '@/Components/Robot/RobotLogs';
import SensorStatusPanel from '@/Components/Robot/SensorStatusPanel';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';

const Diagnostics: LayoutComponent = () => {
    const { telemetry, logs, clearLogs } = useRobotContext();

    return (
        <>
            <Head title="Robot — Diagnostics" />
            <SensorStatusPanel topics={telemetry.heartbeats} />
            <DiagnosticsPanel diagnostics={telemetry.diagnostics} />
            <RobotLogs logs={logs} onClear={clearLogs} />
        </>
    );
};

Diagnostics.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Diagnostics;
