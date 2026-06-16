export type OccupancyGrid = {
    info: {
        width: number;
        height: number;
        resolution: number;
        origin: {
            position: { x: number; y: number; z?: number };
        };
    };
    data: number[];
};

export type RobotPose = {
    x: number;
    y: number;
    yaw: number;
    linearSpeed: number;
    angularSpeed: number;
};

export type NavPath = {
    poses?: Array<{
        pose: {
            position: { x: number; y: number; z?: number };
        };
    }>;
};

export type Waypoint = {
    id: string;
    name: string;
    x: number;
    y: number;
    yaw: number;
};

export type BatteryState = {
    raw: number;
    displayValue: string;
    estimateLabel: string;
    level: 'unknown' | 'good' | 'low' | 'critical';
    updatedAt: string;
};

export type TopicHeartbeat = {
    key: string;
    label: string;
    topic: string;
    lastSeenAt: number | null;
    messageCount: number;
};

export type DiagnosticStatus = {
    id: string;
    name: string;
    level: number;
    message: string;
    hardwareId?: string;
    updatedAt: string;
};

export type ArmJoints = {
    joint1: number;
    joint2: number;
    joint3: number;
    joint4: number;
    joint5: number;
    joint6: number;
    time: number;
};

export type RosApi = {
    publish: (topic: string, type: string, msg: unknown) => boolean;
    callService: (service: string, options?: { type?: string; args?: Record<string, unknown> }) => boolean;
    subscribe: (topic: string, callback: (message: unknown) => void, options?: { type?: string; throttleRate?: number }) => () => void;
    addLog: (message: string, level?: 'info' | 'ok' | 'warn' | 'error') => void;
};
