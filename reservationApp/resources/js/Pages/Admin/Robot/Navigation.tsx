import { Head } from '@inertiajs/react';
import RobotLayout from '@/Layouts/RobotLayout';
import MapCanvas from '@/Components/Robot/MapCanvas';
import RobotActionsPanel from '@/Components/Robot/RobotActionsPanel';
import WaypointList from '@/Components/Robot/WaypointList';
import { useRobotContext } from '@/Components/Robot/RobotContext';
import type { LayoutComponent } from '@/types/inertia';

const Navigation: LayoutComponent = () => {
    const { ros, telemetry, waypoints, addCurrentPoseWaypoint, sendGoal } = useRobotContext();

    return (
        <>
            <Head title="Robot — Navigation" />

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <MapCanvas
                    map={telemetry.map}
                    onGoal={(x, y) => sendGoal(x, y)}
                    path={telemetry.path}
                    pose={telemetry.pose}
                />
                <div className="space-y-6">
                    <RobotActionsPanel pose={telemetry.pose} ros={ros} />
                    <WaypointList
                        onAddCurrentPose={addCurrentPoseWaypoint}
                        onSendWaypoint={(waypoint) => sendGoal(waypoint.x, waypoint.y, waypoint.yaw)}
                        pose={telemetry.pose}
                        ros={ros}
                        waypoints={waypoints}
                    />
                </div>
            </div>
        </>
    );
};

Navigation.layout = (page) => <RobotLayout>{page}</RobotLayout>;

export default Navigation;
