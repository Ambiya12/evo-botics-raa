import { useState } from 'react';
import type { RobotPose, Waypoint } from './types';

type Props = {
    onAddCurrentPose: () => void;
    onRemoveWaypoint: (id: string) => void;
    onRenameWaypoint: (id: string, name: string) => void;
    onSendWaypoint: (waypoint: Waypoint) => void;
    pose: RobotPose | null;
    waypoints: Waypoint[];
};

export default function WaypointList({
    onAddCurrentPose,
    onRemoveWaypoint,
    onRenameWaypoint,
    onSendWaypoint,
    pose,
    waypoints,
}: Props) {
    const [editingId, setEditingId] = useState<string | null>(null);
    const [draftName, setDraftName] = useState('');

    const beginRename = (waypoint: Waypoint) => {
        setEditingId(waypoint.id);
        setDraftName(waypoint.name);
    };

    const finishRename = () => {
        if (!editingId || !draftName.trim()) return;
        onRenameWaypoint(editingId, draftName);
        setEditingId(null);
        setDraftName('');
    };

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div className="flex items-center justify-between gap-3">
                <div>
                    <h3 className="text-sm font-semibold text-gray-900">Waypoints</h3>
                    <p className="text-xs text-gray-500">Saved targets for reception and rooms</p>
                </div>
                <button
                    className="rounded-lg bg-gray-100 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!pose || waypoints.length >= 3}
                    onClick={onAddCurrentPose}
                    type="button"
                >
                    {waypoints.length >= 3 ? '3/3 Saved' : 'Save Pose'}
                </button>
            </div>

            <div className="mt-4 space-y-2">
                {waypoints.length === 0 && (
                    <p className="rounded-lg border border-dashed border-gray-200 p-4 text-center text-xs text-gray-500">
                        No saved waypoints. Save the robot&apos;s current AMCL pose to add one.
                    </p>
                )}
                {waypoints.map((waypoint) => (
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3" key={waypoint.id}>
                        <div className="flex items-center justify-between gap-3">
                            <div className="min-w-0 flex-1">
                                {editingId === waypoint.id ? (
                                    <input
                                        autoFocus
                                        className="w-full rounded-md border border-blue-300 bg-white px-2 py-1 text-sm font-semibold text-gray-900 outline-none focus:ring-2 focus:ring-blue-200"
                                        maxLength={48}
                                        onChange={(event) => setDraftName(event.target.value)}
                                        onKeyDown={(event) => {
                                            if (event.key === 'Enter') finishRename();
                                            if (event.key === 'Escape') setEditingId(null);
                                        }}
                                        value={draftName}
                                    />
                                ) : (
                                    <p className="truncate text-sm font-semibold text-gray-900">{waypoint.name}</p>
                                )}
                                <p className="text-xs text-gray-500">
                                    {waypoint.x.toFixed(2)}, {waypoint.y.toFixed(2)} · yaw {waypoint.yaw.toFixed(2)}
                                </p>
                            </div>
                            <button
                                className="rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold text-white hover:bg-blue-700"
                                onClick={() => onSendWaypoint(waypoint)}
                                type="button"
                            >
                                Go
                            </button>
                        </div>
                        <div className="mt-2 flex gap-2">
                            {editingId === waypoint.id ? (
                                <>
                                    <button
                                        className="text-xs font-semibold text-blue-700 hover:text-blue-900 disabled:opacity-50"
                                        disabled={!draftName.trim()}
                                        onClick={finishRename}
                                        type="button"
                                    >
                                        Save name
                                    </button>
                                    <button
                                        className="text-xs font-semibold text-gray-500 hover:text-gray-700"
                                        onClick={() => setEditingId(null)}
                                        type="button"
                                    >
                                        Cancel
                                    </button>
                                </>
                            ) : (
                                <button
                                    className="text-xs font-semibold text-gray-600 hover:text-gray-900"
                                    onClick={() => beginRename(waypoint)}
                                    type="button"
                                >
                                    Rename
                                </button>
                            )}
                            <button
                                className="text-xs font-semibold text-red-600 hover:text-red-800"
                                onClick={() => {
                                    if (window.confirm(`Remove "${waypoint.name}"?`)) {
                                        onRemoveWaypoint(waypoint.id);
                                    }
                                }}
                                type="button"
                            >
                                Remove
                            </button>
                        </div>
                    </div>
                ))}
            </div>
            <p className="mt-3 text-right text-xs text-gray-400">
                {waypoints.length}/3 saved in this browser
            </p>
        </section>
    );
}
