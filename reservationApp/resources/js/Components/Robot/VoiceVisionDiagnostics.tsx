import type { RobotTelemetry } from '@/hooks/useRobotTelemetry';

type Props = {
    voice: RobotTelemetry['voice'];
};

const value = (text: string) => text || 'Waiting';

export default function VoiceVisionDiagnostics({ voice }: Props) {
    const confidence = voice.intentConfidence === null
        ? 'Waiting'
        : `${Math.round(voice.intentConfidence * 100)}%`;

    const items = [
        ['STT', value(voice.sttStatus), '/voice/stt/status'],
        ['TTS', value(voice.ttsStatus), '/voice/tts/status'],
        ['Dialogue', value(voice.dialogueState), '/reception/dialogue/state'],
        ['Last STT event', value(voice.sttEvent), '/voice/stt/diagnostics'],
        ['Transcript', value(voice.transcript), '/voice/stt/transcript'],
        ['Intent', voice.intent ? `${voice.intent} (${confidence})` : 'Waiting', '/voice/intent/result'],
        ['Human present', voice.personPresent === null ? 'Waiting' : voice.personPresent ? 'Yes' : 'No', '/vision/people/presence'],
        ['Detections', String(voice.personDetectionCount), '/vision/people/detections'],
        [
            'Workflow',
            voice.workflowState
                ? `${voice.workflowState} · ${value(voice.workflowOutcome)}`
                : 'Waiting',
            '/reception/workflow/status',
        ],
        [
            'Reception navigation',
            voice.navigationState
                ? `${voice.navigationState}${voice.navigationDestination ? ` → ${voice.navigationDestination}` : ''}`
                : 'Waiting',
            '/reception/navigation/status',
        ],
    ];

    return (
        <section className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
            <div>
                <h3 className="text-sm font-semibold text-gray-900">Voice & Human Detection</h3>
                <p className="text-xs text-gray-500">Live handoff trace from microphone to dialogue and vision</p>
            </div>

            {voice.sttError && (
                <p className="mt-3 rounded-lg bg-red-50 p-3 text-sm text-red-800">
                    STT error: {voice.sttError}
                </p>
            )}
            {voice.navigationMessage && (
                <p className={`mt-3 rounded-lg p-3 text-sm ${
                    voice.navigationState === 'failed'
                        ? 'bg-red-50 text-red-800'
                        : 'bg-blue-50 text-blue-800'
                }`}>
                    Navigation: {voice.navigationMessage}
                </p>
            )}

            <div className="mt-4 grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
                {items.map(([label, current, topic]) => (
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3" key={label}>
                        <p className="text-xs font-medium text-gray-500">{label}</p>
                        <p className="mt-1 break-words text-sm font-semibold text-gray-900">{current}</p>
                        <p className="mt-1 truncate text-xs text-gray-400">{topic}</p>
                    </div>
                ))}
            </div>
        </section>
    );
}
