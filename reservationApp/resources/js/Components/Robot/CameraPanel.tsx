import { useEffect, useMemo, useState } from 'react';

type Props = {
    cameraUrl: string;
};

type CameraStatus = {
    available?: boolean;
    error?: string | null;
    last_encoding?: string | null;
    opencv_available?: boolean;
    received_frames?: number;
    topic?: string;
};

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

const statusUrlFromStream = (url: string) => (
    snapshotUrlFromStream(url).replace(/\/camera\/snapshot$/, '/camera/status')
);

export default function CameraPanel({ cameraUrl }: Props) {
    const [failed, setFailed] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);
    const [snapshotReady, setSnapshotReady] = useState(false);
    const [snapshotKey, setSnapshotKey] = useState(0);
    const [status, setStatus] = useState<CameraStatus | null>(null);
    const streamUrl = cameraUrl ? urlWithCacheBuster(cameraUrl, reloadKey) : '';
    const snapshotUrl = useMemo(() => (
        cameraUrl ? urlWithCacheBuster(snapshotUrlFromStream(cameraUrl), snapshotKey) : ''
    ), [cameraUrl, snapshotKey]);

    useEffect(() => {
        setFailed(false);
        setSnapshotReady(false);
        setStatus(null);
    }, [cameraUrl, reloadKey]);

    useEffect(() => {
        if (!failed) return undefined;

        let cancelled = false;
        const poll = async () => {
            setSnapshotKey(Date.now());
            try {
                const response = await fetch(urlWithCacheBuster(statusUrlFromStream(cameraUrl), Date.now()), {
                    cache: 'no-store',
                });
                if (response.ok && !cancelled) {
                    setStatus(await response.json() as CameraStatus);
                }
            } catch {
                if (!cancelled) setStatus(null);
            }
        };
        void poll();
        const interval = window.setInterval(poll, 1000);
        return () => {
            cancelled = true;
            window.clearInterval(interval);
        };
    }, [cameraUrl, failed]);

    const reload = () => {
        setFailed(false);
        setSnapshotReady(false);
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
                                    className="h-full w-full object-contain"
                                    onLoad={() => setSnapshotReady(true)}
                                    src={snapshotUrl}
                                />
                                {!snapshotReady && (
                                    <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-950/90 px-6 text-center">
                                        <p className="text-sm font-semibold text-white">Camera stream unavailable</p>
                                        <p className="mt-2 text-xs leading-5 text-gray-400">
                                            {status?.error
                                                ? `Frame conversion failed: ${status.error}`
                                                : status?.opencv_available === false
                                                    ? 'OpenCV is missing in the robot runtime.'
                                                    : status && Number(status.received_frames ?? 0) === 0
                                                        ? `No images received on ${status.topic ?? 'the configured camera topic'}.`
                                                        : 'Waiting for JPEG frames from the robot camera server.'}
                                        </p>
                                        {status?.last_encoding && (
                                            <p className="mt-1 text-xs text-gray-500">
                                                ROS encoding: {status.last_encoding}
                                            </p>
                                        )}
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
