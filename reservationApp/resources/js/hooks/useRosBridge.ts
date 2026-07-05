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

type Publisher = {
    id: string;
    topic: string;
    type: string;
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
    const publishersRef = useRef<Map<string, Publisher>>(new Map());
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
                console.error('[rosbridge] Outbound payload dropped: socket is not open', payload);
            }
            return false;
        }

        console.debug('[rosbridge] Sending payload', payload);
        socket.send(JSON.stringify(payload));
        return true;
    }, [addLog]);

    const resubscribe = useCallback(() => {
        publishersRef.current.forEach((publisher) => {
            send({
                op: 'advertise',
                id: publisher.id,
                topic: publisher.topic,
                type: publisher.type,
                queue_size: 10,
                latch: false,
            });
        });
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

    const ensurePublisher = useCallback((topic: string, type: string) => {
        const current = publishersRef.current.get(topic);
        if (current?.type === type) {
            return true;
        }

        if (current) {
            send({ op: 'unadvertise', id: current.id, topic }, true);
            publishersRef.current.delete(topic);
        }

        const publisher = {
            id: `pub:${topic}:${++requestIdRef.current}`,
            topic,
            type,
        };
        const advertised = send({
            op: 'advertise',
            id: publisher.id,
            topic,
            type,
            queue_size: 10,
            latch: false,
        });
        if (!advertised) {
            return false;
        }

        publishersRef.current.set(topic, publisher);
        return true;
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
            let socket: WebSocket;
            try {
                socket = new WebSocket(url);
            } catch {
                setStatus('error');
                addLog('Invalid rosbridge URL. Check the robot host and ROS port.', 'error');
                return;
            }

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
                } else if (data.op === 'service_response') {
                    console.info('[rosbridge] Service response', data);
                    addLog(
                        `Service response ${data.service ?? data.id ?? ''}: ${data.result === false ? 'failed' : 'received'}`,
                        data.result === false ? 'error' : 'ok',
                    );
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
        if (!ensurePublisher(topic, type)) {
            return false;
        }
        const payload = { op: 'publish', topic, type, msg };
        const ok = send(payload);
        if (ok) {
            addLog(`Sent ${topic} to rosbridge: ${JSON.stringify(msg)}`, 'info');
        }
        return ok;
    }, [addLog, ensurePublisher, send]);

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
