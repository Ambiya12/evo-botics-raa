import { useEffect, useState } from 'react';

type Props = {
    cameraUrl: string;
};

export default function CameraPanel({ cameraUrl }: Props) {
    const [failed, setFailed] = useState(false);
    const [reloadKey, setReloadKey] = useState(0);
    const streamUrl = cameraUrl ? `${cameraUrl}${cameraUrl.includes('?') ? '&' : '?'}t=${reloadKey}` : '';

    useEffect(() => {
        setFailed(false);
    }, [cameraUrl, reloadKey]);

    return (
        <section className="rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Live Camera</h3>
                    <p className="text-xs text-gray-500">MJPEG stream from the robot web server</p>
                </div>
                <button
                    className="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200"
                    onClick={() => setReloadKey(Date.now())}
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
                            className="h-full w-full object-contain"
                            onError={() => setFailed(true)}
                            onLoad={() => setFailed(false)}
                            src={streamUrl}
                        />
                        {failed && (
                            <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-950/90 px-6 text-center">
                                <p className="text-sm font-semibold text-white">Camera stream unavailable</p>
                                <p className="mt-2 text-xs leading-5 text-gray-400">
                                    Check that the robot web server is running and that its camera_topic matches a live ROS image topic.
                                </p>
                            </div>
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
