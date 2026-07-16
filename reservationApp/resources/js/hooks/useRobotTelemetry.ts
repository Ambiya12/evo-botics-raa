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
    diagnosticsFromMessage,
    normalizeBattery,
    poseFromOdom,
    poseFromStampedPose,
} from '@/Components/Robot/transforms';

export const HEARTBEAT_TOPICS: Array<Pick<TopicHeartbeat, 'key' | 'label' | 'topic'>> = [
    { key: 'battery', label: 'Base battery', topic: '/battery' },
    { key: 'map', label: 'Map', topic: '/map' },
    { key: 'odom', label: 'Odometry', topic: '/odom' },
    { key: 'amcl', label: 'AMCL', topic: '/amcl_pose' },
    { key: 'scan', label: 'LiDAR', topic: '/scan' },
    { key: 'imu', label: 'IMU', topic: '/imu/data' },
    { key: 'rgb', label: 'RGB camera', topic: '/camera/color/camera_info' },
    { key: 'depth', label: 'Depth camera', topic: '/camera/depth/camera_info' },
    { key: 'arm', label: 'Arm command route', topic: '/arm6_joints' },
];

const initialHeartbeats = (): TopicHeartbeat[] => HEARTBEAT_TOPICS.map((topic) => ({
    ...topic,
    lastSeenAt: null,
    messageCount: 0,
}));

export type RobotTelemetry = {
    map: OccupancyGrid | null;
    costmap: OccupancyGrid | null;
    path: NavPath | null;
    pose: RobotPose | null;
    battery: BatteryState | null;
    heartbeats: TopicHeartbeat[];
    diagnostics: DiagnosticStatus[];
    armJoints: ArmJoints | null;
    mapSize: string;
    diagnosticsLevel: number | null;
    voice: {
        sttStatus: string;
        ttsStatus: string;
        dialogueState: string;
        transcript: string;
        intent: string;
        intentConfidence: number | null;
        sttEvent: string;
        sttError: string;
        personPresent: boolean | null;
        personDetectionCount: number;
        workflowState: string;
        workflowOutcome: string;
        navigationState: string;
        navigationDestination: string;
        navigationMessage: string;
        updatedAt: number | null;
    };
};

export function useRobotTelemetry(ros: RosApi): RobotTelemetry {
    const [map, setMap] = useState<OccupancyGrid | null>(null);
    const [costmap, setCostmap] = useState<OccupancyGrid | null>(null);
    const [path, setPath] = useState<NavPath | null>(null);
    const [pose, setPose] = useState<RobotPose | null>(null);
    const [battery, setBattery] = useState<BatteryState | null>(null);
    const [heartbeats, setHeartbeats] = useState<TopicHeartbeat[]>(initialHeartbeats);
    const [diagnostics, setDiagnostics] = useState<DiagnosticStatus[]>([]);
    const [armJoints, setArmJoints] = useState<ArmJoints | null>(null);
    const [voice, setVoice] = useState<RobotTelemetry['voice']>({
        sttStatus: 'waiting',
        ttsStatus: 'waiting',
        dialogueState: 'waiting',
        transcript: '',
        intent: '',
        intentConfidence: null,
        sttEvent: '',
        sttError: '',
        personPresent: null,
        personDetectionCount: 0,
        workflowState: '',
        workflowOutcome: '',
        navigationState: '',
        navigationDestination: '',
        navigationMessage: '',
        updatedAt: null,
    });
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

        const unsubscribeCostmap = ros.subscribe('/global_costmap/costmap', (message) => {
            setCostmap(message as OccupancyGrid);
        }, { type: 'nav_msgs/msg/OccupancyGrid', throttleRate: 3000 });

        const unsubscribeOdom = ros.subscribe('/odom', (message) => {
            const odomPose = poseFromOdom(message);
            markTopic('odom');
            if (!odomPose) return;

            // /odom is expressed in the odom frame, while the map canvas needs
            // coordinates in the map frame. AMCL owns map-frame x/y/yaw.
            // Only merge odometry velocities here; otherwise every odom update
            // makes a valid AMCL pose jump back to unrelated odom coordinates.
            setPose((current) => current ? {
                ...current,
                linearSpeed: odomPose.linearSpeed,
                angularSpeed: odomPose.angularSpeed,
            } : current);
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
            markTopic('battery');
            if (next.level !== lastBatteryLevelRef.current) {
                if (next.level === 'low') ros.addLog(`Battery low: ${next.displayValue}`, 'warn');
                if (next.level === 'critical') ros.addLog(`Battery critical: ${next.displayValue}`, 'error');
                lastBatteryLevelRef.current = next.level;
            }
        }, { type: 'std_msgs/msg/Float32', throttleRate: 1000 });

        const unsubscribeDiagnostics = ros.subscribe('/diagnostics', (message) => {
            setDiagnostics(diagnosticsFromMessage(message));
        }, { type: 'diagnostic_msgs/msg/DiagnosticArray', throttleRate: 1000 });

        const updateVoice = (next: Partial<RobotTelemetry['voice']>) => {
            setVoice((current) => ({ ...current, ...next, updatedAt: Date.now() }));
        };
        const voiceUnsubscribers = [
            ros.subscribe('/voice/stt/status', (message: any) => {
                updateVoice({ sttStatus: String(message?.data ?? 'unknown') });
            }, { type: 'std_msgs/msg/String' }),
            ros.subscribe('/voice/tts/status', (message: any) => {
                updateVoice({ ttsStatus: String(message?.data ?? 'unknown') });
            }, { type: 'std_msgs/msg/String' }),
            ros.subscribe('/reception/dialogue/state', (message: any) => {
                updateVoice({ dialogueState: String(message?.data ?? 'unknown') });
            }, { type: 'std_msgs/msg/String' }),
            ros.subscribe('/voice/stt/transcript', (message: any) => {
                updateVoice({ transcript: String(message?.text ?? '') });
            }, { type: 'evo_reception_interfaces/msg/Transcript' }),
            ros.subscribe('/voice/intent/result', (message: any) => {
                updateVoice({
                    intent: String(message?.intent ?? ''),
                    intentConfidence: Number.isFinite(Number(message?.confidence))
                        ? Number(message.confidence)
                        : null,
                });
            }, { type: 'evo_reception_interfaces/msg/IntentResult' }),
            ros.subscribe('/voice/stt/diagnostics', (message: any) => {
                try {
                    const diagnostic = JSON.parse(String(message?.data ?? '{}'));
                    updateVoice({
                        sttEvent: String(diagnostic?.event ?? ''),
                        sttError: String(diagnostic?.error ?? ''),
                    });
                } catch {
                    updateVoice({ sttEvent: 'invalid_diagnostic', sttError: String(message?.data ?? '') });
                }
            }, { type: 'std_msgs/msg/String' }),
            ros.subscribe('/vision/people/presence', (message: any) => {
                updateVoice({ personPresent: Boolean(message?.data) });
            }, { type: 'std_msgs/msg/Bool' }),
            ros.subscribe('/vision/people/detections', () => {
                setVoice((current) => ({
                    ...current,
                    personDetectionCount: current.personDetectionCount + 1,
                    updatedAt: Date.now(),
                }));
            }, { type: 'evo_reception_interfaces/msg/PersonDetection', throttleRate: 100 }),
            ros.subscribe('/reception/workflow/status', (message: any) => {
                updateVoice({
                    workflowState: String(message?.state ?? ''),
                    workflowOutcome: String(message?.outcome ?? ''),
                });
            }, { type: 'evo_reception_interfaces/msg/WorkflowStatus' }),
            ros.subscribe('/reception/navigation/status', (message: any) => {
                updateVoice({
                    navigationState: String(message?.state ?? ''),
                    navigationDestination: String(message?.destination_id ?? ''),
                    navigationMessage: String(message?.message ?? ''),
                });
            }, { type: 'evo_reception_interfaces/msg/NavigationStatus' }),
        ];

        // Yahboom does not expose servo-position feedback. Its /joint_states
        // publisher contains a synthetic URDF state with model-specific names,
        // so mirror the command that actually reached the MCU input topic.
        const unsubscribeArmCommands = ros.subscribe('/arm6_joints', (message) => {
            markTopic('arm');
            const next = armFromArmMessage(message);
            if (next) setArmJoints(next);
        }, { type: 'arm_msgs/msg/ArmJoints', throttleRate: 100 });

        const heartbeatUnsubscribers = [
            ros.subscribe('/scan', () => markTopic('scan'), { type: 'sensor_msgs/msg/LaserScan', throttleRate: 1000 }),
            ros.subscribe('/imu/data', () => markTopic('imu'), { type: 'sensor_msgs/msg/Imu', throttleRate: 1000 }),
            // CameraInfo provides the same liveness signal without making
            // rosbridge serialize multi-megabyte raw image frames.
            ros.subscribe('/camera/color/camera_info', () => markTopic('rgb'), { type: 'sensor_msgs/msg/CameraInfo', throttleRate: 1000 }),
            ros.subscribe('/camera/depth/camera_info', () => markTopic('depth'), { type: 'sensor_msgs/msg/CameraInfo', throttleRate: 1000 }),
        ];

        return () => {
            unsubscribeMap();
            unsubscribeCostmap();
            unsubscribeOdom();
            unsubscribeAmclPose();
            unsubscribePath();
            unsubscribeBattery();
            unsubscribeDiagnostics();
            unsubscribeArmCommands();
            voiceUnsubscribers.forEach((unsubscribe) => unsubscribe());
            heartbeatUnsubscribers.forEach((unsubscribe) => unsubscribe());
        };
    }, [markTopic, ros]);

    const mapSize = map ? `${map.info.width} x ${map.info.height} @ ${map.info.resolution.toFixed(2)}m` : '';
    const diagnosticsLevel = diagnostics.length ? Math.max(...diagnostics.map((item) => item.level)) : null;

    return useMemo(() => ({
        map, costmap, path, pose, battery, heartbeats, diagnostics, armJoints, mapSize, diagnosticsLevel, voice,
    }), [map, costmap, path, pose, battery, heartbeats, diagnostics, armJoints, mapSize, diagnosticsLevel, voice]);
}
