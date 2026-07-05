import type { ArmJoints, BatteryState, DiagnosticStatus, OccupancyGrid, RobotPose } from './types';

export const normalizeBattery = (raw: number): BatteryState => {
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

const yawFromQuaternion = (q: any): number => Math.atan2(
    2 * ((q.w ?? 1) * (q.z ?? 0) + (q.x ?? 0) * (q.y ?? 0)),
    1 - 2 * ((q.y ?? 0) * (q.y ?? 0) + (q.z ?? 0) * (q.z ?? 0)),
);

export const poseFromOdom = (message: any): RobotPose | null => {
    const pose = message?.pose?.pose;
    const twist = message?.twist?.twist;
    if (!pose?.position || !pose?.orientation) return null;

    return {
        x: Number(pose.position.x ?? 0),
        y: Number(pose.position.y ?? 0),
        yaw: yawFromQuaternion(pose.orientation),
        linearSpeed: Math.hypot(Number(twist?.linear?.x ?? 0), Number(twist?.linear?.y ?? 0)),
        angularSpeed: Number(twist?.angular?.z ?? 0),
    };
};

export const poseFromStampedPose = (message: any, previous: RobotPose | null): RobotPose | null => {
    const pose = message?.pose?.pose;
    if (!pose?.position || !pose?.orientation) return null;

    return {
        x: Number(pose.position.x ?? 0),
        y: Number(pose.position.y ?? 0),
        yaw: yawFromQuaternion(pose.orientation),
        linearSpeed: previous?.linearSpeed ?? 0,
        angularSpeed: previous?.angularSpeed ?? 0,
    };
};

export const quaternionFromYaw = (yaw: number) => ({
    x: 0,
    y: 0,
    z: Math.sin(yaw / 2),
    w: Math.cos(yaw / 2),
});

export const occupancyAtWorld = (
    grid: OccupancyGrid,
    worldX: number,
    worldY: number,
): number | null => {
    const origin = grid.info.origin;
    const yaw = yawFromQuaternion(origin.orientation ?? {});
    const dx = worldX - origin.position.x;
    const dy = worldY - origin.position.y;
    const localX = Math.cos(yaw) * dx + Math.sin(yaw) * dy;
    const localY = -Math.sin(yaw) * dx + Math.cos(yaw) * dy;
    const cellX = Math.floor(localX / grid.info.resolution);
    const cellY = Math.floor(localY / grid.info.resolution);

    if (
        cellX < 0
        || cellY < 0
        || cellX >= grid.info.width
        || cellY >= grid.info.height
    ) {
        return null;
    }

    return Number(grid.data[cellY * grid.info.width + cellX] ?? -1);
};

export const hasOccupancyClearance = (
    grid: OccupancyGrid,
    worldX: number,
    worldY: number,
    clearanceMeters: number,
    occupiedThreshold: number,
): boolean => {
    const radiusCells = Math.ceil(clearanceMeters / grid.info.resolution);
    const yaw = yawFromQuaternion(grid.info.origin.orientation ?? {});

    for (let cellY = -radiusCells; cellY <= radiusCells; cellY += 1) {
        for (let cellX = -radiusCells; cellX <= radiusCells; cellX += 1) {
            if (Math.hypot(cellX, cellY) > radiusCells) continue;
            const localX = cellX * grid.info.resolution;
            const localY = cellY * grid.info.resolution;
            const value = occupancyAtWorld(
                grid,
                worldX + Math.cos(yaw) * localX - Math.sin(yaw) * localY,
                worldY + Math.sin(yaw) * localX + Math.cos(yaw) * localY,
            );
            if (value === null || value < 0 || value >= occupiedThreshold) {
                return false;
            }
        }
    }

    return true;
};

export const armFromArmMessage = (message: any): ArmJoints | null => {
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

export const armFromJointState = (message: any): ArmJoints | null => {
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

export const diagnosticsFromMessage = (message: any): DiagnosticStatus[] => {
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
