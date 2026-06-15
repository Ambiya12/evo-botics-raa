import { Head } from '@inertiajs/react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import AuthenticatedLayout from '@/Layouts/AuthenticatedLayout';
import ArmControlPanel from '@/Components/Robot/ArmControlPanel';
import CameraPanel from '@/Components/Robot/CameraPanel';
import ConnectionStatus from '@/Components/Robot/ConnectionStatus';
import DiagnosticsPanel from '@/Components/Robot/DiagnosticsPanel';
import EmergencyStopButton from '@/Components/Robot/EmergencyStopButton';
import ManualControls from '@/Components/Robot/ManualControls';
import MapCanvas from '@/Components/Robot/MapCanvas';
import RobotActionsPanel from '@/Components/Robot/RobotActionsPanel';
import RobotHealthCards from '@/Components/Robot/RobotHealthCards';
import RobotLogs from '@/Components/Robot/RobotLogs';
import SensorStatusPanel from '@/Components/Robot/SensorStatusPanel';
import WaypointList from '@/Components/Robot/WaypointList';
import type {
    ArmJoints,
    BatteryState,
    DiagnosticStatus,
    NavPath,
    OccupancyGrid,
    RobotPose,
    RosApi,
    TopicHeartbeat,
    Waypoint,
} from '@/Components/Robot/types';
import { useRosBridge } from '@/hooks/useRosBridge';

const DEFAULT_WAYPOINTS: Waypoint[] = [
    { id: 'reception', name: 'Reception', x: 0, y: 0, yaw: 0 },
    { id: 'room-a', name: 'Meeting Room A', x: 1.5, y: 0.5, yaw: 0 },
    { id: 'room-b', name: 'Meeting Room B', x: 2.2, y: -0.8, yaw: 0 },
];

const HEARTBEAT_TOPICS: Array<Pick<TopicHeartbeat, 'key' | 'label' | 'topic'>> = [
    { key: 'map', label: 'Map', topic: '/map' },
    { key: 'odom', label: 'Odometry', topic: '/odom' },
    { key: 'amcl', label: 'AMCL', topic: '/amcl_pose' },
    { key: 'scan', label: 'LiDAR', topic: '/scan' },
    { key: 'imu', label: 'IMU', topic: '/imu/data' },
    { key: 'rgb', label: 'RGB camera', topic: '/camera/color/camera_info' },
    { key: 'depth', label: 'Depth camera', topic: '/camera/depth/camera_info' },
    { key: 'arm', label: 'Arm joints', topic: '/joint_states' },
];

const initialHeartbeats = (): TopicHeartbeat[] => HEARTBEAT_TOPICS.map((topic) => ({
    ...topic,
    lastSeenAt: null,
    messageCount: 0,
}));

const normalizeBattery = (raw: number): BatteryState => {
    const updatedAt = new Date().toLocaleTimeString();

    if (!Number.isFinite(raw)) {
        return {
            raw: 0,
            displayValue: 'Unknown',
            estimateLabel: 'Invalid battery value',
            level: 'unknown',
            updatedAt,
        };
    }

    if (raw >= 5 && raw <= 30) {
        const estimatedPercent = Math.max(0, Math.min(100, Math.round(((raw - 10.5) / (12.6 - 10.5)) * 100)));
        const level = estimatedPercent <= 15 ? 'critical' : estimatedPercent <= 30 ? 'low' : 'good';

        return {
            raw,
            displayValue: `${raw.toFixed(2)} V`,
            estimateLabel: `Estimated ${estimatedPercent}%`,
            level,
            updatedAt,
        };
    }

    if (raw >= 0 && raw <= 100) {
        const level = raw <= 15 ? 'critical' : raw <= 30 ? 'low' : 'good';

        return {
            raw,
            displayValue: `${Math.round(raw)}%`,
            estimateLabel: 'Reported percentage',
            level,
            updatedAt,
        };
    }

    return {
        raw,
        displayValue: raw.toFixed(2),
        estimateLabel: 'Raw /battery value',
        level: 'unknown',
        updatedAt,
    };
};

const poseFromOdom = (message: any): RobotPose | null => {
    const pose = message?.pose?.pose;
    const twist = message?.twist?.twist;
    if (!pose?.position || !pose?.orientation) return null;

    const q = pose.orientation;
    const yaw = Math.atan2(
        2 * ((q.w ?? 1) * (q.z ?? 0) + (q.x ?? 0) * (q.y ?? 0)),
        1 - 2 * ((q.y ?? 0) * (q.y ?? 0) + (q.z ?? 0) * (q.z ?? 0)),
    );

    return {
        x: Number(pose.position.x ?? 0),
        y: Number(pose.position.y ?? 0),
        yaw,
        linearSpeed: Math.hypot(Number(twist?.linear?.x ?? 0), Number(twist?.linear?.y ?? 0)),
        angularSpeed: Number(twist?.angular?.z ?? 0),
    };
};

const poseFromStampedPose = (message: any, previous: RobotPose | null): RobotPose | null => {
    const pose = message?.pose?.pose;
    if (!pose?.position || !pose?.orientation) return null;

    const q = pose.orientation;
    const yaw = Math.atan2(
        2 * ((q.w ?? 1) * (q.z ?? 0) + (q.x ?? 0) * (q.y ?? 0)),
        1 - 2 * ((q.y ?? 0) * (q.y ?? 0) + (q.z ?? 0) * (q.z ?? 0)),
    );

    return {
        x: Number(pose.position.x ?? 0),
        y: Number(pose.position.y ?? 0),
        yaw,
        linearSpeed: previous?.linearSpeed ?? 0,
        angularSpeed: previous?.angularSpeed ?? 0,
    };
};

const quaternionFromYaw = (yaw: number) => ({
    x: 0,
    y: 0,
    z: Math.sin(yaw / 2),
    w: Math.cos(yaw / 2),
});

const armFromArmMessage = (message: any): ArmJoints | null => {
    if (!message) return null;
    const keys: Array<keyof Omit<ArmJoints, 'time'>> = ['joint1', 'joint2', 'joint3', 'joint4', 'joint5', 'joint6'];
    if (!keys.every((key) => Number.isFinite(Number(message[key])))) return null;

    return {
        joint1: Math.round(Number(message.joint1)),
        joint2: Math.round(Number(message.joint2)),
        joint3: Math.round(Number(message.joint3)),
        joint4: Math.round(Number(message.joint4)),
        joint5: Math.round(Number(message.joint5)),
        joint6: Math.round(Number(message.joint6)),
        time: Number(message.time ?? 800),
    };
};

const armFromJointState = (message: any): ArmJoints | null => {
    if (!Array.isArray(message?.name) || !Array.isArray(message?.position)) return null;

    const current: ArmJoints = { joint1: 90, joint2: 120, joint3: 10, joint4: 20, joint5: 90, joint6: 30, time: 800 };
    const jointMap: Record<string, keyof ArmJoints> = {
        base_yaw_joint: 'joint1',
        shoulder_joint: 'joint2',
        elbow_joint: 'joint3',
        wrist_pitch_joint: 'joint4',
        wrist_roll_joint: 'joint5',
    };

    let matched = false;
    message.name.forEach((name: string, index: number) => {
        const key = jointMap[name];
        if (!key) return;
        const value = Number(message.position[index]);
        if (!Number.isFinite(value)) return;
        current[key] = Math.max(0, Math.min(180, Math.round(90 + (value * 180) / Math.PI)));
        matched = true;
    });

    const fingerIndex = message.name.findIndex((name: string) => name === 'left_finger_joint' || name === 'right_finger_joint');
    if (fingerIndex >= 0) {
        const fingerOpenMeters = Number(message.position[fingerIndex]);
        if (Number.isFinite(fingerOpenMeters)) {
            current.joint6 = Math.max(20, Math.min(150, Math.round(90 - (fingerOpenMeters / 0.04) * 60)));
            matched = true;
        }
    }

    return matched ? current : null;
};

const diagnosticsFromMessage = (message: any): DiagnosticStatus[] => {
    if (!Array.isArray(message?.status)) return [];
    const updatedAt = new Date().toLocaleTimeString();

    return message.status.map((status: any, index: number) => ({
        id: `${status?.hardware_id ?? 'diagnostic'}:${status?.name ?? index}`,
        name: String(status?.name ?? `Diagnostic ${index + 1}`),
        level: Number(status?.level ?? 3),
        message: String(status?.message ?? ''),
        hardwareId: status?.hardware_id ? String(status.hardware_id) : undefined,
        updatedAt,
    }));
};

export default function RobotDashboard() {
    const [robotHost, setRobotHost] = useState('10.10.221.115');
    const [rosPort, setRosPort] = useState('9090');
    const [cameraPort, setCameraPort] = useState('8080');
    const [cameraPath, setCameraPath] = useState('/camera/stream');
    const [mapSavePath, setMapSavePath] = useState('/root/maps/admin_map');
    const [map, setMap] = useState<OccupancyGrid | null>(null);
    const [path, setPath] = useState<NavPath | null>(null);
    const [pose, setPose] = useState<RobotPose | null>(null);
    const [waypoints, setWaypoints] = useState<Waypoint[]>(DEFAULT_WAYPOINTS);
    const [battery, setBattery] = useState<BatteryState | null>(null);
    const [heartbeats, setHeartbeats] = useState<TopicHeartbeat[]>(initialHeartbeats);
    const [diagnostics, setDiagnostics] = useState<DiagnosticStatus[]>([]);
    const [armJoints, setArmJoints] = useState<ArmJoints | null>(null);
    const lastBatteryLevelRef = useRef<BatteryState['level'] | null>(null);

    const rosUrl = useMemo(() => `ws://${robotHost}:${rosPort}`, [robotHost, rosPort]);
    const cameraUrl = useMemo(() => {
        const normalizedPath = cameraPath.startsWith('/') ? cameraPath : `/${cameraPath}`;
        return `http://${robotHost}:${cameraPort}${normalizedPath}`;
    }, [cameraPath, cameraPort, robotHost]);
    const rosBridge = useRosBridge(rosUrl);

    const ros: RosApi = useMemo(() => ({
        addLog: rosBridge.addLog,
        callService: rosBridge.callService,
        publish: rosBridge.publish,
        subscribe: rosBridge.subscribe,
    }), [rosBridge.addLog, rosBridge.callService, rosBridge.publish, rosBridge.subscribe]);

    const markTopic = useCallback((key: string) => {
        const now = Date.now();
        setHeartbeats((current) => current.map((topic) => (
            topic.key === key
                ? { ...topic, lastSeenAt: now, messageCount: topic.messageCount + 1 }
                : topic
        )));
    }, []);

    useEffect(() => {
        const unsubscribeMap = ros.subscribe('/map', (message) => {
            setMap(message as OccupancyGrid);
            markTopic('map');
        }, { type: 'nav_msgs/msg/OccupancyGrid', throttleRate: 500 });

        const unsubscribeOdom = ros.subscribe('/odom', (message) => {
            const nextPose = poseFromOdom(message);
            markTopic('odom');
            if (nextPose) setPose((current) => ({ ...nextPose, yaw: current?.yaw ?? nextPose.yaw }));
        }, { type: 'nav_msgs/msg/Odometry', throttleRate: 150 });

        const unsubscribeAmclPose = ros.subscribe('/amcl_pose', (message) => {
            markTopic('amcl');
            setPose((current) => poseFromStampedPose(message, current) ?? current);
        }, { type: 'geometry_msgs/msg/PoseWithCovarianceStamped', throttleRate: 250 });

        const unsubscribePath = ros.subscribe('/plan', (message) => {
            setPath(message as NavPath);
        }, { type: 'nav_msgs/msg/Path', throttleRate: 500 });

        const unsubscribeBattery = ros.subscribe('/battery', (message: any) => {
            const next = normalizeBattery(Number(message?.data));
            setBattery(next);
            if (next.level !== lastBatteryLevelRef.current) {
                if (next.level === 'low') ros.addLog(`Battery low: ${next.displayValue}`, 'warn');
                if (next.level === 'critical') ros.addLog(`Battery critical: ${next.displayValue}`, 'error');
                lastBatteryLevelRef.current = next.level;
            }
        }, { type: 'std_msgs/msg/Float32', throttleRate: 1000 });

        const unsubscribeDiagnostics = ros.subscribe('/diagnostics', (message) => {
            setDiagnostics(diagnosticsFromMessage(message));
        }, { type: 'diagnostic_msgs/msg/DiagnosticArray', throttleRate: 1000 });

        const unsubscribeArm6 = ros.subscribe('/arm6_joints', (message) => {
            const next = armFromArmMessage(message);
            if (next) setArmJoints(next);
        }, { type: 'arm_msgs/msg/ArmJoints', throttleRate: 300 });

        const unsubscribeJointStates = ros.subscribe('/joint_states', (message) => {
            markTopic('arm');
            const next = armFromJointState(message);
            if (next) setArmJoints(next);
        }, { type: 'sensor_msgs/msg/JointState', throttleRate: 500 });

        const heartbeatUnsubscribers = [
            ros.subscribe('/scan', () => markTopic('scan'), { type: 'sensor_msgs/msg/LaserScan', throttleRate: 1000 }),
            ros.subscribe('/imu/data', () => markTopic('imu'), { type: 'sensor_msgs/msg/Imu', throttleRate: 1000 }),
            ros.subscribe('/camera/color/camera_info', () => markTopic('rgb'), { type: 'sensor_msgs/msg/CameraInfo', throttleRate: 1000 }),
            ros.subscribe('/camera/depth/camera_info', () => markTopic('depth'), { type: 'sensor_msgs/msg/CameraInfo', throttleRate: 1000 }),
        ];

        return () => {
            unsubscribeMap();
            unsubscribeOdom();
            unsubscribeAmclPose();
            unsubscribePath();
            unsubscribeBattery();
            unsubscribeDiagnostics();
            unsubscribeArm6();
            unsubscribeJointStates();
            heartbeatUnsubscribers.forEach((unsubscribe) => unsubscribe());
        };
    }, [markTopic, ros]);

    const sendGoal = (x: number, y: number, yaw = 0) => {
        ros.publish('/goal_pose', 'geometry_msgs/msg/PoseStamped', {
            header: { frame_id: 'map' },
            pose: {
                position: { x, y, z: 0 },
                orientation: quaternionFromYaw(yaw),
            },
        });
        ros.addLog(`Navigation goal sent to ${x.toFixed(2)}, ${y.toFixed(2)}`, 'ok');
    };

    const saveMap = () => {
        ros.callService('/slam_toolbox/save_map', {
            type: 'slam_toolbox/srv/SaveMap',
            args: { name: { data: mapSavePath } },
        });
        ros.addLog(`Map save requested: ${mapSavePath}`, 'info');
    };

    const addCurrentPoseWaypoint = () => {
        if (!pose) return;
        const nextNumber = waypoints.length + 1;
        setWaypoints((current) => [
            ...current,
            {
                id: `waypoint-${Date.now()}`,
                name: `Waypoint ${nextNumber}`,
                x: pose.x,
                y: pose.y,
                yaw: pose.yaw,
            },
        ]);
        ros.addLog(`Saved waypoint from current pose: ${pose.x.toFixed(2)}, ${pose.y.toFixed(2)}`, 'ok');
    };

    const mapSize = map ? `${map.info.width} x ${map.info.height} @ ${map.info.resolution.toFixed(2)}m` : '';
    const diagnosticsLevel = diagnostics.length ? Math.max(...diagnostics.map((item) => item.level)) : null;

    return (
        <AuthenticatedLayout
            header={
                <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div>
                        <h2 className="text-xl font-semibold leading-tight text-gray-800">Robot Admin Dashboard</h2>
                        <p className="mt-1 text-sm text-gray-500">Camera, map, Nav2 goals, manual control, and safety tools.</p>
                    </div>
                    <EmergencyStopButton ros={ros} />
                </div>
            }
        >
            <Head title="Robot Admin Dashboard" />

            <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 lg:px-8">
                <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
                    <div className="grid gap-3 md:grid-cols-5">
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Robot IP
                            <input
                                className="mt-2 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setRobotHost(event.target.value)}
                                type="text"
                                value={robotHost}
                            />
                        </label>
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            ROS port
                            <input
                                className="mt-2 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setRosPort(event.target.value)}
                                type="text"
                                value={rosPort}
                            />
                        </label>
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Camera port
                            <input
                                className="mt-2 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setCameraPort(event.target.value)}
                                type="text"
                                value={cameraPort}
                            />
                        </label>
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Camera path
                            <input
                                className="mt-2 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                onChange={(event) => setCameraPath(event.target.value)}
                                type="text"
                                value={cameraPath}
                            />
                        </label>
                        <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500">
                            Save map path
                            <div className="mt-2 flex gap-2">
                                <input
                                    className="w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                                    onChange={(event) => setMapSavePath(event.target.value)}
                                    type="text"
                                    value={mapSavePath}
                                />
                                <button
                                    className="rounded-lg bg-gray-900 px-3 py-2 text-xs font-semibold text-white hover:bg-gray-700"
                                    onClick={saveMap}
                                    type="button"
                                >
                                    Save
                                </button>
                            </div>
                        </label>
                    </div>
                </section>

                <ConnectionStatus
                    cameraUrl={cameraUrl}
                    lastMessageAt={rosBridge.lastMessageAt}
                    rosUrl={rosUrl}
                    status={rosBridge.status}
                />

                <RobotHealthCards battery={battery} diagnosticsLevel={diagnosticsLevel} mapSize={mapSize} pose={pose} />

                <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                    <div className="space-y-6">
                        <MapCanvas map={map} onGoal={(x, y) => sendGoal(x, y)} path={path} pose={pose} />
                        <SensorStatusPanel topics={heartbeats} />
                        <DiagnosticsPanel diagnostics={diagnostics} />
                        <RobotLogs logs={rosBridge.logs} onClear={rosBridge.clearLogs} />
                    </div>

                    <div className="space-y-6">
                        <CameraPanel cameraUrl={cameraUrl} />
                        <ManualControls ros={ros} />
                        <RobotActionsPanel pose={pose} ros={ros} />
                        <ArmControlPanel currentJoints={armJoints} ros={ros} />
                        <WaypointList
                            onAddCurrentPose={addCurrentPoseWaypoint}
                            onSendWaypoint={(waypoint) => sendGoal(waypoint.x, waypoint.y, waypoint.yaw)}
                            pose={pose}
                            ros={ros}
                            waypoints={waypoints}
                        />
                    </div>
                </div>
            </div>
        </AuthenticatedLayout>
    );
}
