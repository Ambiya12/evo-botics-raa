import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import ArmStateView from '@/Components/Robot/ArmStateView';
import CameraPanel from '@/Components/Robot/CameraPanel';
import MapCanvas from '@/Components/Robot/MapCanvas';
import RobotHealthCards from '@/Components/Robot/RobotHealthCards';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';
import { useTranslation } from '@/hooks/useTranslation';

const Overview: LayoutComponent = () => {
    const { t } = useTranslation();
    const { cameraUrl, ros, telemetry } = useRobotContext();
    const rgb = telemetry.heartbeats.find((topic) => topic.key === 'rgb');
    const cameraOnline = rgb?.lastSeenAt != null && Date.now() - rgb.lastSeenAt < 5000;

    return (
        <>
            <Head title="Robot — Overview" />

            <RobotHealthCards
                battery={telemetry.battery}
                diagnosticsLevel={telemetry.diagnosticsLevel}
                mapSize={telemetry.mapSize}
                pose={telemetry.pose}
            />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <MapCanvas map={telemetry.map} path={telemetry.path} pose={telemetry.pose} />
                <div className="space-y-6">
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">{t('Camera')}</span>
                            <span className={`rounded-full px-2 py-1 text-xs font-semibold ring-1 ${cameraOnline ? 'bg-emerald-100 text-emerald-800 ring-emerald-200' : 'bg-gray-100 text-gray-700 ring-gray-200'}`}>
                                {cameraOnline ? 'On' : 'Off'}
                            </span>
                        </div>
                        <CameraPanel cameraUrl={cameraUrl} ros={ros} />
                    </div>
                    <ArmStateView joints={telemetry.armJoints} />
                </div>
            </div>
        </>
    );
};

Overview.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Overview;
