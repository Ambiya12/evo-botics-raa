import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
    ArmJoints,
    BatteryState,
    DiagnosticStatus,
    NavPath,
    OccupancyGrid,
    RobotPose,
    RosApi,
    TopicHeartbeat,
} from '@/Components/Robot/types';
import {
    armFromArmMessage,
    armFromJointState,
    diagnosticsFromMessage,
    normalizeBattery,
    poseFromOdom,
    poseFromStampedPose,
} from '@/Components/Robot/transforms';

export const HEARTBEAT_TOPICS: Array<Pick<TopicHeartbeat, 'key' | 'label' | 'topic'>> = [
    { key: 'map', label: 'Map', topic: '/map' },
    { key: 'odom', label: 'Odometry', topic: '/odom' },
    { key: 'amcl', label: 'AMCL', topic: '/amcl_pose' },
    { key: 'scan', label: 'LiDAR', topic: '/scan' },
    { key: 'imu', label: 'IMU', topic: '/imu/data' },
    { key: 'rgb', label: 'RGB camera', topic: '/camera/color/image_raw' },
    { key: 'depth', label: 'Depth camera', topic: '/camera/depth/image_raw' },
    { key: 'arm', label: 'Arm joints', topic: '/joint_states' },
];

const initialHeartbeats = (): TopicHeartbeat[] => HEARTBEAT_TOPICS.map((topic) => ({
    ...topic,
    lastSeenAt: null,
    messageCount: 0,
}));

export type RobotTelemetry = {
    map: OccupancyGrid | null;
    path: NavPath | null;
    pose: RobotPose | null;
    battery: BatteryState | null;
    heartbeats: TopicHeartbeat[];
    diagnostics: DiagnosticStatus[];
    armJoints: ArmJoints | null;
    mapSize: string;
    diagnosticsLevel: number | null;
};

export function useRobotTelemetry(ros: RosApi): RobotTelemetry {
    const [map, setMap] = useState<OccupancyGrid | null>(null);
    const [path, setPath] = useState<NavPath | null>(null);
    const [pose, setPose] = useState<RobotPose | null>(null);
    const [battery, setBattery] = useState<BatteryState | null>(null);
    const [heartbeats, setHeartbeats] = useState<TopicHeartbeat[]>(initialHeartbeats);
    const [diagnostics, setDiagnostics] = useState<DiagnosticStatus[]>([]);
    const [armJoints, setArmJoints] = useState<ArmJoints | null>(null);
    const lastBatteryLevelRef = useRef<BatteryState['level'] | null>(null);

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
            ros.subscribe('/camera/color/image_raw', () => markTopic('rgb'), { type: 'sensor_msgs/msg/Image', throttleRate: 1000 }),
            ros.subscribe('/camera/depth/image_raw', () => markTopic('depth'), { type: 'sensor_msgs/msg/Image', throttleRate: 1000 }),
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

    const mapSize = map ? `${map.info.width} x ${map.info.height} @ ${map.info.resolution.toFixed(2)}m` : '';
    const diagnosticsLevel = diagnostics.length ? Math.max(...diagnostics.map((item) => item.level)) : null;

    return useMemo(() => ({
        map, path, pose, battery, heartbeats, diagnostics, armJoints, mapSize, diagnosticsLevel,
    }), [map, path, pose, battery, heartbeats, diagnostics, armJoints, mapSize, diagnosticsLevel]);
}
