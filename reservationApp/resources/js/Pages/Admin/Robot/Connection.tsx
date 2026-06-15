import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import ConnectionSettings from '@/Components/Robot/ConnectionSettings';
import ConnectionStatus from '@/Components/Robot/ConnectionStatus';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';

const Connection: LayoutComponent = () => {
    const { cameraUrl, lastMessageAt, rosUrl, status } = useRobotContext();

    return (
        <>
            <Head title="Robot — Connection" />
            <ConnectionSettings />
            <ConnectionStatus cameraUrl={cameraUrl} lastMessageAt={lastMessageAt} rosUrl={rosUrl} status={status} />
        </>
    );
};

Connection.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Connection;
