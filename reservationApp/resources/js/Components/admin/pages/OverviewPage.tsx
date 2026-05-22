import { CurrentVisitorSessionPanel } from "../CurrentVisitorSessionPanel";
import { RobotHealthPanel } from "../RobotHealthPanel";
import { RobotStatusOverview } from "../RobotStatusOverview";
import { TimeSeriesPanel } from "../TimeSeriesPanel";
import type { RobotStatus, VisitorSession } from "../../../types/admin";

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
      <TimeSeriesPanel />
    </>
  );
}
