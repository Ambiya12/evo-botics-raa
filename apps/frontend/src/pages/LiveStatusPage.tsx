import { ArmStatusPanel } from "../components/admin/ArmStatusPanel";
import { JetsonMetricsPanel } from "../components/admin/JetsonMetricsPanel";
import { TimeSeriesPanel } from "../components/admin/TimeSeriesPanel";
import { VideoFeedPanel } from "../components/admin/VideoFeedPanel";

export function LiveStatusPage() {
  return (
    <>
      <TimeSeriesPanel />
      <div className="dashboard-grid dashboard-grid--robot-details">
        <ArmStatusPanel />
        <JetsonMetricsPanel />
        <VideoFeedPanel />
      </div>
    </>
  );
}
