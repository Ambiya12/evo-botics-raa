import { ArmStatusPanel } from "../ArmStatusPanel";
import { JetsonMetricsPanel } from "../JetsonMetricsPanel";
import { TimeSeriesPanel } from "../TimeSeriesPanel";
import { VideoFeedPanel } from "../VideoFeedPanel";

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
