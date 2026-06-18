import {
    createContext,
    useCallback,
    useContext,
    useMemo,
    useState,
    type ReactNode,
} from "react";
import {
    useRosBridge,
    type RosLogEntry,
    type RosStatus,
} from "@/hooks/useRosBridge";
import {
    useRobotTelemetry,
    type RobotTelemetry,
} from "@/hooks/useRobotTelemetry";
import { quaternionFromYaw } from "@/Components/Robot/transforms";
import type { RosApi, Waypoint } from "@/Components/Robot/types";

const DEFAULT_WAYPOINTS: Waypoint[] = [
    { id: "reception", name: "Reception", x: 0, y: 0, yaw: 0 },
    { id: "room-a", name: "Meeting Room A", x: 1.5, y: 0.5, yaw: 0 },
    { id: "room-b", name: "Meeting Room B", x: 2.2, y: -0.8, yaw: 0 },
];

type RobotConfig = {
    robotHost: string;
    rosPort: string;
    cameraPort: string;
    cameraPath: string;
    mapSavePath: string;
};

type RobotContextValue = {
    config: RobotConfig;
    setConfig: <K extends keyof RobotConfig>(
        key: K,
        value: RobotConfig[K],
    ) => void;
    rosUrl: string;
    cameraUrl: string;
    status: RosStatus;
    lastMessageAt: string | null;
    logs: RosLogEntry[];
    clearLogs: () => void;
    ros: RosApi;
    telemetry: RobotTelemetry;
    waypoints: Waypoint[];
    addCurrentPoseWaypoint: () => void;
    sendGoal: (x: number, y: number, yaw?: number) => void;
    saveMap: () => void;
};

const RobotContext = createContext<RobotContextValue | null>(null);

export function RobotProvider({ children }: { children: ReactNode }) {
    const [config, setConfigState] = useState<RobotConfig>({
        robotHost: "10.10.220.251",
        rosPort: "9090",
        cameraPort: "8080",
        cameraPath: "/camera/stream",
        mapSavePath: "/root/maps/admin_map",
    });

    const setConfig = useCallback(
        <K extends keyof RobotConfig>(key: K, value: RobotConfig[K]) => {
            setConfigState((current) => ({ ...current, [key]: value }));
        },
        [],
    );

    const rosUrl = useMemo(
        () => `ws://${config.robotHost}:${config.rosPort}`,
        [config.robotHost, config.rosPort],
    );
    const cameraUrl = useMemo(() => {
        const normalizedPath = config.cameraPath.startsWith("/")
            ? config.cameraPath
            : `/${config.cameraPath}`;
        return `http://${config.robotHost}:${config.cameraPort}${normalizedPath}`;
    }, [config.cameraPath, config.cameraPort, config.robotHost]);

    const rosBridge = useRosBridge(rosUrl);

    const ros: RosApi = useMemo(
        () => ({
            addLog: rosBridge.addLog,
            callService: rosBridge.callService,
            publish: rosBridge.publish,
            subscribe: rosBridge.subscribe,
        }),
        [
            rosBridge.addLog,
            rosBridge.callService,
            rosBridge.publish,
            rosBridge.subscribe,
        ],
    );

    const telemetry = useRobotTelemetry(ros);
    const [waypoints, setWaypoints] = useState<Waypoint[]>(DEFAULT_WAYPOINTS);

    const sendGoal = useCallback(
        (x: number, y: number, yaw = 0) => {
            ros.publish("/goal_pose", "geometry_msgs/msg/PoseStamped", {
                header: { frame_id: "map" },
                pose: {
                    position: { x, y, z: 0 },
                    orientation: quaternionFromYaw(yaw),
                },
            });
            ros.addLog(
                `Navigation goal sent to ${x.toFixed(2)}, ${y.toFixed(2)}`,
                "ok",
            );
        },
        [ros],
    );

    const saveMap = useCallback(() => {
        ros.callService("/slam_toolbox/save_map", {
            type: "slam_toolbox/srv/SaveMap",
            args: { name: { data: config.mapSavePath } },
        });
        ros.addLog(`Map save requested: ${config.mapSavePath}`, "info");
    }, [ros, config.mapSavePath]);

    const addCurrentPoseWaypoint = useCallback(() => {
        const { pose } = telemetry;
        if (!pose) return;
        setWaypoints((current) => [
            ...current,
            {
                id: `waypoint-${Date.now()}`,
                name: `Waypoint ${current.length + 1}`,
                x: pose.x,
                y: pose.y,
                yaw: pose.yaw,
            },
        ]);
        ros.addLog(
            `Saved waypoint from current pose: ${pose.x.toFixed(2)}, ${pose.y.toFixed(2)}`,
            "ok",
        );
    }, [ros, telemetry]);

    const value = useMemo<RobotContextValue>(
        () => ({
            config,
            setConfig,
            rosUrl,
            cameraUrl,
            status: rosBridge.status,
            lastMessageAt: rosBridge.lastMessageAt,
            logs: rosBridge.logs,
            clearLogs: rosBridge.clearLogs,
            ros,
            telemetry,
            waypoints,
            addCurrentPoseWaypoint,
            sendGoal,
            saveMap,
        }),
        [
            config,
            setConfig,
            rosUrl,
            cameraUrl,
            rosBridge.status,
            rosBridge.lastMessageAt,
            rosBridge.logs,
            rosBridge.clearLogs,
            ros,
            telemetry,
            waypoints,
            addCurrentPoseWaypoint,
            sendGoal,
            saveMap,
        ],
    );

    return (
        <RobotContext.Provider value={value}>{children}</RobotContext.Provider>
    );
}

export function useRobotContext(): RobotContextValue {
    const context = useContext(RobotContext);
    if (!context) {
        throw new Error("useRobotContext must be used within a RobotProvider");
    }
    return context;
}
