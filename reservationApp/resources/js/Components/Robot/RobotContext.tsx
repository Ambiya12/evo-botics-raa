import {
    createContext,
    useCallback,
    useContext,
    useEffect,
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
import {
    hasOccupancyClearance,
    occupancyAtWorld,
    quaternionFromYaw,
} from "@/Components/Robot/transforms";
import type { RosApi, Waypoint } from "@/Components/Robot/types";

const DEFAULT_WAYPOINTS: Waypoint[] = [];

const ROBOT_CONFIG_STORAGE_KEY = "robot.connection.config";
const ROBOT_WAYPOINTS_STORAGE_KEY = "robot.navigation.waypoints";
const MAX_SAVED_WAYPOINTS = 3;

const DEFAULT_CONFIG: RobotConfig = {
    robotHost: "",
    rosPort: "9090",
    cameraPort: "8080",
    cameraPath: "/camera/stream",
    mapSavePath: "/root/maps/new_map",
    goalRequestTopic: "/evo/navigation/goal_request",
    goalStatusTopic: "/evo/navigation/goal_status",
    navigationActionName: "/navigate_to_pose",
    goalFrame: "map",
};

export type RobotConfig = {
    robotHost: string;
    rosPort: string;
    cameraPort: string;
    cameraPath: string;
    mapSavePath: string;
    goalRequestTopic: string;
    goalStatusTopic: string;
    navigationActionName: string;
    goalFrame: string;
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
    removeWaypoint: (id: string) => void;
    renameWaypoint: (id: string, name: string) => void;
    sendGoal: (x: number, y: number, yaw?: number) => void;
    saveMap: () => void;
};

const RobotContext = createContext<RobotContextValue | null>(null);

const normalizeHost = (value: string) => (
    value
        .trim()
        .replace(/^[a-z]+:\/\//i, "")
        .replace(/\/.*$/, "")
);

const isValidPort = (value: string) => {
    const port = Number(value.trim());
    return Number.isInteger(port) && port > 0 && port <= 65535;
};

const loadStoredConfig = (): RobotConfig => {
    if (typeof window === "undefined") {
        return DEFAULT_CONFIG;
    }

    try {
        const stored = window.localStorage.getItem(ROBOT_CONFIG_STORAGE_KEY);
        if (!stored) {
            return DEFAULT_CONFIG;
        }

        return { ...DEFAULT_CONFIG, ...JSON.parse(stored) };
    } catch {
        return DEFAULT_CONFIG;
    }
};

const loadStoredWaypoints = (): Waypoint[] => {
    if (typeof window === "undefined") {
        return DEFAULT_WAYPOINTS;
    }

    try {
        const stored = window.localStorage.getItem(ROBOT_WAYPOINTS_STORAGE_KEY);
        if (!stored) {
            return DEFAULT_WAYPOINTS;
        }

        const parsed = JSON.parse(stored);
        if (!Array.isArray(parsed)) {
            return DEFAULT_WAYPOINTS;
        }

        return parsed
            .filter((waypoint): waypoint is Waypoint => (
                waypoint
                && typeof waypoint.id === "string"
                && typeof waypoint.name === "string"
                && Number.isFinite(waypoint.x)
                && Number.isFinite(waypoint.y)
                && Number.isFinite(waypoint.yaw)
            ))
            .slice(0, MAX_SAVED_WAYPOINTS);
    } catch {
        return DEFAULT_WAYPOINTS;
    }
};

export function RobotProvider({ children }: { children: ReactNode }) {
    const [config, setConfigState] = useState<RobotConfig>(loadStoredConfig);

    const setConfig = useCallback(
        <K extends keyof RobotConfig>(key: K, value: RobotConfig[K]) => {
            setConfigState((current) => ({ ...current, [key]: value }));
        },
        [],
    );

    useEffect(() => {
        try {
            window.localStorage.setItem(
                ROBOT_CONFIG_STORAGE_KEY,
                JSON.stringify(config),
            );
        } catch {
            // Storage is only a convenience; connection controls should still work.
        }
    }, [config]);

    const normalizedHost = useMemo(
        () => normalizeHost(config.robotHost),
        [config.robotHost],
    );

    const rosUrl = useMemo(() => {
        if (!normalizedHost || !isValidPort(config.rosPort)) {
            return "";
        }

        return `ws://${normalizedHost}:${config.rosPort.trim()}`;
    }, [config.rosPort, normalizedHost]);

    const cameraUrl = useMemo(() => {
        if (!normalizedHost || !isValidPort(config.cameraPort)) {
            return "";
        }

        const normalizedPath = config.cameraPath.startsWith("/")
            ? config.cameraPath
            : `/${config.cameraPath}`;
        return `http://${normalizedHost}:${config.cameraPort.trim()}${normalizedPath}`;
    }, [config.cameraPath, config.cameraPort, normalizedHost]);

    const rosBridge = useRosBridge(rosUrl, Boolean(rosUrl));

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
    const [waypoints, setWaypoints] = useState<Waypoint[]>(loadStoredWaypoints);

    useEffect(() => {
        try {
            window.localStorage.setItem(
                ROBOT_WAYPOINTS_STORAGE_KEY,
                JSON.stringify(waypoints),
            );
        } catch {
            // Waypoint persistence is a dashboard convenience; ROS remains authoritative.
        }
    }, [waypoints]);

    useEffect(() => ros.subscribe(config.goalStatusTopic, (message) => {
        const code = typeof message === "object" && message !== null && "data" in message
            ? String((message as { data?: unknown }).data ?? "")
            : "";
        if (!code) return;

        const level = code === "succeeded"
            ? "ok"
            : code === "planning" || code === "accepted" || code === "active"
                ? "info"
                : code === "cancelled"
                    ? "warn"
                    : "error";
        ros.addLog(`Navigation status: ${code}`, level);
        console.info("[navigation] ROS goal status", { topic: config.goalStatusTopic, code });
    }, {
        type: "std_msgs/msg/String",
    }), [config.goalStatusTopic, ros]);

    const sendGoal = useCallback(
        (x: number, y: number, yaw?: number) => {
            if (!telemetry.pose) {
                ros.addLog(
                    "Navigation goal rejected by dashboard: set and verify the AMCL pose first.",
                    "error",
                );
                return;
            }
            const { costmap } = telemetry;
            if (costmap) {
                const robotCost = occupancyAtWorld(
                    costmap,
                    telemetry.pose.x,
                    telemetry.pose.y,
                );
                if (robotCost === null || robotCost < 0 || robotCost >= 95) {
                    ros.addLog(
                        "Navigation goal rejected by dashboard: the current AMCL pose overlaps an occupied or unknown costmap cell. Correct the initial pose.",
                        "error",
                    );
                    return;
                }
                if (!hasOccupancyClearance(costmap, x, y, 0.25, 95)) {
                    ros.addLog(
                        "Navigation goal rejected by dashboard: choose a point in the center of a clear corridor, away from live obstacles and inflated walls.",
                        "error",
                    );
                    return;
                }
            } else {
                // The browser's costmap is advisory telemetry delivered through
                // rosbridge. Do not make it a second mandatory safety gate:
                // navigation_goal_validator owns the authoritative ROS-side
                // map, costmap, clearance, path, and E-stop checks.
                ros.addLog(
                    "Live costmap is not yet visible in the dashboard; forwarding the request to the robot safety validator.",
                    "warn",
                );
            }
            const goalYaw = yaw ?? Math.atan2(
                y - telemetry.pose.y,
                x - telemetry.pose.x,
            );
            if (!Number.isFinite(x) || !Number.isFinite(y) || !Number.isFinite(goalYaw)) {
                ros.addLog("Navigation goal rejected by dashboard: coordinates are not finite.", "error");
                return;
            }
            const payload = {
                header: { frame_id: config.goalFrame },
                pose: {
                    position: { x, y, z: 0 },
                    orientation: quaternionFromYaw(goalYaw),
                },
            };
            console.info("[navigation] Publishing goal request", {
                topic: config.goalRequestTopic,
                payload,
            });
            const sent = ros.publish(
                config.goalRequestTopic,
                "geometry_msgs/msg/PoseStamped",
                payload,
            );
            ros.addLog(
                sent
                    ? `Navigation goal requested at ${x.toFixed(2)}, ${y.toFixed(2)} in ${config.goalFrame}`
                    : `Navigation goal could not be sent at ${x.toFixed(2)}, ${y.toFixed(2)}`,
                sent ? "ok" : "error",
            );
        },
        [config.goalFrame, config.goalRequestTopic, ros, telemetry.costmap, telemetry.pose],
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
        if (waypoints.length >= MAX_SAVED_WAYPOINTS) {
            ros.addLog(
                `Only ${MAX_SAVED_WAYPOINTS} dashboard waypoints can be saved. Remove one before saving another.`,
                "warn",
            );
            return;
        }

        const usedNumbers = new Set(
            waypoints
                .map((waypoint) => waypoint.name.match(/^Waypoint ([1-3])$/)?.[1])
                .filter(Boolean)
                .map(Number),
        );
        const availableNumber = [1, 2, 3].find((number) => !usedNumbers.has(number))
            ?? waypoints.length + 1;
        const waypoint: Waypoint = {
            id: `waypoint-${Date.now()}`,
            name: `Waypoint ${availableNumber}`,
            x: pose.x,
            y: pose.y,
            yaw: pose.yaw,
        };
        setWaypoints((current) => [...current, waypoint]);
        ros.addLog(
            `Saved ${waypoint.name} from current pose: ${pose.x.toFixed(2)}, ${pose.y.toFixed(2)}`,
            "ok",
        );
    }, [ros, telemetry, waypoints]);

    const removeWaypoint = useCallback((id: string) => {
        const waypoint = waypoints.find((item) => item.id === id);
        if (!waypoint) return;
        setWaypoints((current) => current.filter((item) => item.id !== id));
        ros.addLog(`Removed waypoint: ${waypoint.name}`, "info");
    }, [ros, waypoints]);

    const renameWaypoint = useCallback((id: string, name: string) => {
        const trimmedName = name.trim();
        if (!trimmedName) {
            ros.addLog("Waypoint name cannot be empty.", "warn");
            return;
        }
        setWaypoints((current) => current.map((waypoint) => (
            waypoint.id === id ? { ...waypoint, name: trimmedName } : waypoint
        )));
        ros.addLog(`Renamed waypoint to: ${trimmedName}`, "ok");
    }, [ros]);

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
            removeWaypoint,
            renameWaypoint,
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
            removeWaypoint,
            renameWaypoint,
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
