import { useRobotContext } from './RobotContext';

const FIELDS: Array<{ key: 'robotHost' | 'rosPort' | 'cameraPort' | 'cameraPath'; label: string }> = [
    { key: 'robotHost', label: 'Robot IP' },
    { key: 'rosPort', label: 'ROS port' },
    { key: 'cameraPort', label: 'Camera port' },
    { key: 'cameraPath', label: 'Camera path' },
];

export default function ConnectionSettings() {
    const { config, setConfig, saveMap } = useRobotContext();

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div>
                <h3 className="text-sm font-semibold text-gray-900">Connection Settings</h3>
                <p className="text-xs text-gray-500">Robot host, ports, camera and map saving</p>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
                {FIELDS.map((field) => (
                    <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500" key={field.key}>
                        {field.label}
                        <input
                            className="mt-2 w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                            onChange={(event) => setConfig(field.key, event.target.value)}
                            type="text"
                            value={config[field.key]}
                        />
                    </label>
                ))}

                <label className="block text-xs font-semibold uppercase tracking-wide text-gray-500 md:col-span-2">
                    Save map path
                    <div className="mt-2 flex gap-2">
                        <input
                            className="w-full rounded-lg border-gray-300 text-sm shadow-sm focus:border-blue-500 focus:ring-blue-500"
                            onChange={(event) => setConfig('mapSavePath', event.target.value)}
                            type="text"
                            value={config.mapSavePath}
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
    );
}
