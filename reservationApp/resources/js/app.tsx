import "../css/app.css";
import "./bootstrap";

import { setEventLogProvider } from "@/services/eventLogService";
import { setIncidentProvider } from "@/services/incidentService";
import { setConnectionManagerStatus } from "@/services/providers/connectionManagerStore";
import { createLaravelEchoEventLogProvider } from "@/services/providers/laravelEchoEventLogProvider";
import { createLaravelEchoIncidentProvider } from "@/services/providers/laravelEchoIncidentProvider";
import { createLaravelEchoRobotDataProvider } from "@/services/providers/laravelEchoRobotDataProvider";
import { createLaravelEchoVisitorSessionProvider } from "@/services/providers/laravelEchoVisitorSessionProvider";
import { createWebSocketConnectionManager } from "@/services/providers/websocketConnectionManager";
import { setRobotStatusProvider } from "@/services/robotStatusService";
import { pruneOldMetrics } from "@/services/timeSeriesStore";
import { setVisitorSessionProvider } from "@/services/visitorSessionService";
import { createInertiaApp } from "@inertiajs/react";
import { resolvePageComponent } from "laravel-vite-plugin/inertia-helpers";
import { createRoot } from "react-dom/client";

void pruneOldMetrics();

if (import.meta.env.VITE_USE_REAL_ROBOT === "true") {
    const wsUrl = `${import.meta.env.VITE_REVERB_SCHEME}://${import.meta.env.VITE_REVERB_HOST}:${import.meta.env.VITE_REVERB_PORT}`;
    const manager = createWebSocketConnectionManager(
        wsUrl,
        import.meta.env.VITE_REVERB_APP_KEY as string,
    );
    manager.subscribe(setConnectionManagerStatus);
    setRobotStatusProvider(createLaravelEchoRobotDataProvider(manager));
    setVisitorSessionProvider(createLaravelEchoVisitorSessionProvider(manager));
    setEventLogProvider(createLaravelEchoEventLogProvider(manager));
    setIncidentProvider(createLaravelEchoIncidentProvider(manager));
}

const appName = import.meta.env.VITE_APP_NAME || "Laravel";

createInertiaApp({
    title: (title) => `${title} - ${appName}`,
    resolve: (name) =>
        resolvePageComponent(
            `./Pages/${name}.tsx`,
            import.meta.glob("./Pages/**/*.tsx"),
        ),
    setup({ el, App, props }) {
        const root = createRoot(el);

        root.render(<App {...props} />);
    },
    progress: {
        color: "#4B5563",
    },
});
