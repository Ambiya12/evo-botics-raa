import { useEffect, useMemo, useRef, useState } from 'react';
import type { RosApi } from '@/Components/Robot/types';

type Props = {
    cameraUrl: string;
    ros: Pick<RosApi, 'subscribe'>;
};

type RosImageMessage = {
    data?: number[] | string;
    encoding?: string;
    height?: number;
    step?: number;
    width?: number;
};

const CAMERA_TOPIC = '/camera/color/image_raw';

const urlWithCacheBuster = (url: string, value: number) => (
    `${url}${url.includes('?') ? '&' : '?'}t=${value}`
);

const snapshotUrlFromStream = (url: string) => {
    try {
        const parsed = new URL(url);
        parsed.pathname = parsed.pathname.replace(/\/camera\/stream$/, '/camera/snapshot');
        parsed.search = '';
        return parsed.toString();
    } catch {
        return url.replace(/\/camera\/stream(?:\?.*)?$/, '/camera/snapshot');
    }
};

const bytesFromRosData = (data: RosImageMessage['data']) => {
    if (Array.isArray(data)) {
        return Uint8Array.from(data);
    }

    if (typeof data === 'string') {
        try {
            const binary = window.atob(data);
            const bytes = new Uint8Array(binary.length);
            for (let index = 0; index < binary.length; index += 1) {
                bytes[index] = binary.charCodeAt(index);
            }
            return bytes;
        } catch {
            return null;
        }
    }

    return null;
};

const drawRosImage = (canvas: HTMLCanvasElement, message: RosImageMessage) => {
    const width = Number(message.width);
    const height = Number(message.height);
    const encoding = String(message.encoding ?? '').toLowerCase();
    const step = Number(message.step || 0);
    const bytes = bytesFromRosData(message.data);

    if (!width || !height || !bytes) {
        return false;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) {
        return false;
    }

    canvas.width = width;
    canvas.height = height;

    const image = ctx.createImageData(width, height);
    const rgba = image.data;
    const rowStride = step || width * (encoding === 'rgba8' || encoding === 'bgra8' ? 4 : 3);

    if (encoding === 'rgb8' || encoding === 'bgr8') {
        for (let y = 0; y < height; y += 1) {
            for (let x = 0; x < width; x += 1) {
                const source = y * rowStride + x * 3;
                const target = (y * width + x) * 4;
                rgba[target] = encoding === 'rgb8' ? bytes[source] : bytes[source + 2];
                rgba[target + 1] = bytes[source + 1];
                rgba[target + 2] = encoding === 'rgb8' ? bytes[source + 2] : bytes[source];
                rgba[target + 3] = 255;
            }
        }
    } else if (encoding === 'rgba8' || encoding === 'bgra8') {
        for (let y = 0; y < height; y += 1) {
            for (let x = 0; x < width; x += 1) {
                const source = y * rowStride + x * 4;
                const target = (y * width + x) * 4;
                rgba[target] = encoding === 'rgba8' ? bytes[source] : bytes[source + 2];
                rgba[target + 1] = bytes[source + 1];
                rgba[target + 2] = encoding === 'rgba8' ? bytes[source + 2] : bytes[source];
                rgba[target + 3] = bytes[source + 3] ?? 255;
            }
        }
    } else if (encoding === 'mono8' || encoding === '8uc1') {
        const monoStride = step || width;
        for (let y = 0; y < height; y += 1) {
            for (let x = 0; x < width; x += 1) {
                const value = bytes[y * monoStride + x];
                const target = (y * width + x) * 4;
                rgba[target] = value;
                rgba[target + 1] = value;
                rgba[target + 2] = value;
                rgba[target + 3] = 255;
            }
        }
    } else {
        return false;
    }

    ctx.putImageData(image, 0, 0);
    return true;
};

export default function CameraPanel({ cameraUrl, ros }: Props) {
    const [failed, setFailed] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);
    const [snapshotReady, setSnapshotReady] = useState(false);
    const [rosFrameReady, setRosFrameReady] = useState(false);
    const [snapshotKey, setSnapshotKey] = useState(0);
    const canvasRef = useRef<HTMLCanvasElement | null>(null);
    const streamUrl = cameraUrl ? urlWithCacheBuster(cameraUrl, reloadKey) : '';
    const snapshotUrl = useMemo(() => (
        cameraUrl ? urlWithCacheBuster(snapshotUrlFromStream(cameraUrl), snapshotKey) : ''
    ), [cameraUrl, snapshotKey]);

    useEffect(() => {
        setFailed(false);
        setSnapshotReady(false);
        setRosFrameReady(false);
    }, [cameraUrl, reloadKey]);

    useEffect(() => {
        if (!failed) return undefined;

        const interval = window.setInterval(() => setSnapshotKey(Date.now()), 300);
        return () => window.clearInterval(interval);
    }, [failed]);

    useEffect(() => {
        if (!failed) return undefined;

        return ros.subscribe(CAMERA_TOPIC, (message) => {
            const canvas = canvasRef.current;
            if (!canvas) return;

            const drawn = drawRosImage(canvas, message as RosImageMessage);
            if (drawn) {
                setRosFrameReady(true);
            }
        }, { type: 'sensor_msgs/msg/Image', throttleRate: 250 });
    }, [failed, ros]);

    const reload = () => {
        setFailed(false);
        setSnapshotReady(false);
        setRosFrameReady(false);
        setReloadKey(Date.now());
        setSnapshotKey(Date.now());
    };

    return (
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Live Camera</h3>
                    <p className="text-xs text-gray-500">Robot web stream with ROS image fallback</p>
                </div>
                <button
                    className="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200"
                    onClick={reload}
                    type="button"
                >
                    Reload
                </button>
            </div>
            <div className="relative aspect-video bg-gray-950">
                {cameraUrl ? (
                    <>
                        <img
                            alt="Robot camera stream"
                            className={`h-full w-full object-contain ${failed ? 'hidden' : ''}`}
                            onError={() => setFailed(true)}
                            src={streamUrl}
                        />
                        {failed && (
                            <>
                                <img
                                    alt="Robot camera snapshot"
                                    className={`h-full w-full object-contain ${rosFrameReady ? 'hidden' : ''}`}
                                    onLoad={() => {
                                        setSnapshotReady(true);
                                        setRosFrameReady(false);
                                    }}
                                    src={snapshotUrl}
                                />
                                <canvas
                                    aria-label="Robot camera ROS image"
                                    className={`h-full w-full object-contain ${rosFrameReady ? '' : 'hidden'}`}
                                    ref={canvasRef}
                                />
                                {!snapshotReady && !rosFrameReady && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-950/90 px-6 text-center">
                                        <p className="text-sm font-semibold text-white">Camera stream unavailable</p>
                                        <p className="mt-2 text-xs leading-5 text-gray-400">
                                            Waiting for JPEG frames from the robot web server or raw images from {CAMERA_TOPIC}.
                                        </p>
                                    </div>
                                )}
                            </>
                        )}
                    </>
                ) : (
                    <div className="flex h-full items-center justify-center text-sm text-gray-400">
                        Configure a camera URL
                    </div>
                )}
            </div>
        </section>
    );
}
