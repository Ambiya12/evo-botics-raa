import { CurrentVisitorSessionPanel } from "../components/admin/CurrentVisitorSessionPanel";
import { EventLogTable } from "../components/admin/EventLogTable";
import type { EventLog, VisitorSession } from "../types/admin";

interface SessionsPageProps {
  currentSession: VisitorSession | null;
  logs: EventLog[];
}

export function SessionsPage({ currentSession, logs }: SessionsPageProps) {
  return (
    <>
      <div className="dashboard-grid">
        <CurrentVisitorSessionPanel session={currentSession} />
        <EventLogTable logs={logs} />
      </div>
    </>
  );
}
