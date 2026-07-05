import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import MapCanvas from '@/Components/Robot/MapCanvas';
import RobotActionsPanel from '@/Components/Robot/RobotActionsPanel';
import WaypointList from '@/Components/Robot/WaypointList';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';

const Navigation: LayoutComponent = () => {
    const {
        config,
        ros,
        telemetry,
        waypoints,
        addCurrentPoseWaypoint,
        removeWaypoint,
        renameWaypoint,
        sendGoal,
    } = useRobotContext();

    return (
        <>
            <Head title="Robot — Navigation" />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <MapCanvas
                    costmap={telemetry.costmap}
                    map={telemetry.map}
                    onGoal={(x, y) => sendGoal(x, y)}
                    path={telemetry.path}
                    pose={telemetry.pose}
                />
                <div className="space-y-6">
                    <RobotActionsPanel
                        navigationActionName={config.navigationActionName}
                        pose={telemetry.pose}
                        ros={ros}
                    />
                    <WaypointList
                        onAddCurrentPose={addCurrentPoseWaypoint}
                        onRemoveWaypoint={removeWaypoint}
                        onRenameWaypoint={renameWaypoint}
                        onSendWaypoint={(waypoint) => sendGoal(waypoint.x, waypoint.y, waypoint.yaw)}
                        pose={telemetry.pose}
                        waypoints={waypoints}
                    />
                </div>
            </div>
        </>
    );
};

Navigation.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Navigation;
