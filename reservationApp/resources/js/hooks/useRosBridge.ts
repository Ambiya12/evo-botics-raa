import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

export type RosStatus = 'idle' | 'connecting' | 'connected' | 'disconnected' | 'error';

export type RosLogLevel = 'info' | 'ok' | 'warn' | 'error';

export type RosLogEntry = {
    id: number;
    at: string;
    level: RosLogLevel;
    message: string;
};

type RosEnvelope = {
    op?: string;
    id?: string;
    topic?: string;
    msg?: unknown;
    values?: unknown;
    service?: string;
    result?: boolean;
};

type Subscriber = {
    options: SubscribeOptions;
    topic: string;
    callback: (message: unknown) => void;
};

type SubscribeOptions = {
    type?: string;
    throttleRate?: number;
};

type ServiceOptions = {
    type?: string;
    args?: Record<string, unknown>;
};

const MAX_LOGS = 120;

export function useRosBridge(url: string, enabled = true) {
    const socketRef = useRef<WebSocket | null>(null);
    const reconnectTimerRef = useRef<number | null>(null);
    const subscribersRef = useRef<Map<string, Subscriber>>(new Map());
    const requestIdRef = useRef(0);
    const logIdRef = useRef(0);
    const [status, setStatus] = useState<RosStatus>('idle');
    const [lastMessageAt, setLastMessageAt] = useState<string | null>(null);
    const [logs, setLogs] = useState<RosLogEntry[]>([]);

    const addLog = useCallback((message: string, level: RosLogLevel = 'info') => {
        const now = new Date();
        setLogs((current) => [
            ...current.slice(-(MAX_LOGS - 1)),
            {
                id: ++logIdRef.current,
                at: now.toLocaleTimeString(),
                level,
                message,
            },
        ]);
    }, []);

    const send = useCallback((payload: Record<string, unknown>, silent = false) => {
        const socket = socketRef.current;
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            if (!silent) {
                addLog('ROS command ignored because rosbridge is not connected.', 'warn');
            }
            return false;
        }

        socket.send(JSON.stringify(payload));
        return true;
    }, [addLog]);

    const resubscribe = useCallback(() => {
        subscribersRef.current.forEach((sub, id) => {
            send({
                op: 'subscribe',
                id,
                topic: sub.topic,
                type: sub.options.type,
                throttle_rate: sub.options.throttleRate,
            });
        });
    }, [send]);

    useEffect(() => {
        if (!enabled || !url) {
            setStatus('idle');
            return;
        }

        let closedByEffect = false;

        const connect = () => {
            setStatus('connecting');
            addLog(`Connecting to ${url}`, 'info');
            const socket = new WebSocket(url);
            socketRef.current = socket;

            socket.onopen = () => {
                setStatus('connected');
                addLog('Connected to rosbridge.', 'ok');
                resubscribe();
            };

            socket.onmessage = (event) => {
                setLastMessageAt(new Date().toLocaleTimeString());
                let data: RosEnvelope;
                try {
                    data = JSON.parse(event.data);
                } catch {
                    return;
                }

                if (data.op === 'publish' && data.topic && data.msg !== undefined) {
                    subscribersRef.current.forEach((sub) => {
                        if (sub.topic === data.topic) {
                            sub.callback(data.msg);
                        }
                    });
                }
            };

            socket.onerror = () => {
                setStatus('error');
                addLog('rosbridge connection error.', 'error');
            };

            socket.onclose = () => {
                if (socketRef.current === socket) {
                    socketRef.current = null;
                }
                if (closedByEffect) {
                    return;
                }
                setStatus('disconnected');
                addLog('rosbridge disconnected. Retrying in 3 seconds.', 'warn');
                reconnectTimerRef.current = window.setTimeout(connect, 3000);
            };
        };

        connect();

        return () => {
            closedByEffect = true;
            if (reconnectTimerRef.current) {
                window.clearTimeout(reconnectTimerRef.current);
            }
            socketRef.current?.close();
            socketRef.current = null;
        };
    }, [addLog, enabled, resubscribe, url]);

    const subscribe = useCallback((
        topic: string,
        callback: (message: unknown) => void,
        options: SubscribeOptions = {},
    ) => {
        const id = `sub:${topic}:${++requestIdRef.current}`;
        subscribersRef.current.set(id, { topic, callback, options });
        send({
            op: 'subscribe',
            id,
            topic,
            type: options.type,
            throttle_rate: options.throttleRate,
        }, true);

        return () => {
            subscribersRef.current.delete(id);
            send({ op: 'unsubscribe', id, topic }, true);
        };
    }, [send]);

    const publish = useCallback((topic: string, type: string, msg: unknown) => {
        const ok = send({ op: 'publish', topic, type, msg });
        if (ok) {
            addLog(`Published ${topic}`, 'info');
        }
        return ok;
    }, [addLog, send]);

    const callService = useCallback((service: string, options: ServiceOptions = {}) => {
        const id = `srv:${service}:${++requestIdRef.current}`;
        const ok = send({
            op: 'call_service',
            id,
            service,
            type: options.type,
            args: options.args ?? {},
        });
        if (ok) {
            addLog(`Called service ${service}`, 'info');
        }
        return ok;
    }, [addLog, send]);

    const clearLogs = useCallback(() => setLogs([]), []);

    return useMemo(() => ({
        addLog,
        callService,
        clearLogs,
        lastMessageAt,
        logs,
        publish,
        status,
        subscribe,
    }), [addLog, callService, clearLogs, lastMessageAt, logs, publish, status, subscribe]);
}
