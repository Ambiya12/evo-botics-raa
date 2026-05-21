import { CurrentVisitorSessionPanel } from "../components/admin/CurrentVisitorSessionPanel";
import { RobotHealthPanel } from "../components/admin/RobotHealthPanel";
import { RobotStatusOverview } from "../components/admin/RobotStatusOverview";
import type { RobotStatus, VisitorSession } from "../types/admin";

interface OverviewPageProps {
  robotStatus: RobotStatus;
  currentSession: VisitorSession | null;
}

export function OverviewPage({ robotStatus, currentSession }: OverviewPageProps) {
  return (
    <>
      <RobotStatusOverview robotStatus={robotStatus} />
      <div className="dashboard-grid">
        <RobotHealthPanel robotStatus={robotStatus} />
        <CurrentVisitorSessionPanel session={currentSession} />
      </div>
    </>
  );
}
