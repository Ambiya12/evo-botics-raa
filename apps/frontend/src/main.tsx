import React from "react";
import ReactDOM from "react-dom/client";
import { AdminDashboard } from "./app/AdminDashboard";
import { pruneOldMetrics } from "./services/timeSeriesStore";
import "./styles.css";

async function bootstrap(): Promise<void> {
  await pruneOldMetrics();

  const reverbUrl = import.meta.env.VITE_REVERB_URL as string | undefined;
  const reverbKey = import.meta.env.VITE_REVERB_APP_KEY as string | undefined;

  if (reverbUrl && reverbKey) {
    const [
      { createWebSocketConnectionManager },
      { createLaravelEchoRobotDataProvider },
      { createLaravelEchoVisitorSessionProvider },
      { createLaravelEchoEventLogProvider },
      { createLaravelEchoIncidentProvider },
      { setRobotStatusProvider },
      { setVisitorSessionProvider },
      { setEventLogProvider },
      { setIncidentProvider },
      { setConnectionManagerStatus },
    ] = await Promise.all([
      import("./services/providers/websocketConnectionManager"),
      import("./services/providers/laravelEchoRobotDataProvider"),
      import("./services/providers/laravelEchoVisitorSessionProvider"),
      import("./services/providers/laravelEchoEventLogProvider"),
      import("./services/providers/laravelEchoIncidentProvider"),
      import("./services/robotStatusService"),
      import("./services/visitorSessionService"),
      import("./services/eventLogService"),
      import("./services/incidentService"),
      import("./services/providers/connectionManagerStore"),
    ]);

    const manager = createWebSocketConnectionManager(reverbUrl, reverbKey);
    manager.subscribe((status) => setConnectionManagerStatus(status));
    setConnectionManagerStatus("connecting");

    setRobotStatusProvider(createLaravelEchoRobotDataProvider(manager));
    setVisitorSessionProvider(createLaravelEchoVisitorSessionProvider(manager));
    setEventLogProvider(createLaravelEchoEventLogProvider(manager));
    setIncidentProvider(createLaravelEchoIncidentProvider(manager));
  }

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <AdminDashboard />
    </React.StrictMode>,
  );
}

void bootstrap();
