import { CircleStop, Pause, Play, Radio, RotateCcw, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Panel } from "../ui/Panel";

interface SafetyActionsProps {
  emergencyStopActive: boolean;
  onEmergencyStop: () => Promise<void>;
}

export function SafetyActions({
  emergencyStopActive,
  onEmergencyStop,
}: SafetyActionsProps) {
  const [isConfirming, setIsConfirming] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleEmergencyStopClick = async () => {
    if (emergencyStopActive || isSubmitting) {
      return;
    }

    if (!isConfirming) {
      setIsConfirming(true);
      return;
    }

    setIsSubmitting(true);

    try {
      await onEmergencyStop();
      setIsConfirming(false);
    } finally {
      setIsSubmitting(false);
    }
  };

  const emergencyStopLabel = emergencyStopActive
    ? "Emergency stop active"
    : isConfirming
      ? "Confirm stop"
      : "Emergency stop";

  return (
    <Panel
      className="safety-panel"
      eyebrow="Safety controls"
      title="Operator actions"
      action={<ShieldCheck aria-hidden="true" size={20} strokeWidth={1.8} />}
    >
      <button
        className={`emergency-button ${isConfirming ? "emergency-button--confirming" : ""}`}
        type="button"
        onClick={() => {
          void handleEmergencyStopClick();
        }}
        disabled={emergencyStopActive || isSubmitting}
      >
        <CircleStop aria-hidden="true" size={19} />
        {emergencyStopLabel}
      </button>

      {!emergencyStopActive && isConfirming ? (
        <p className="safety-panel__hint">Press again to dispatch the mock stop command.</p>
      ) : null}

      <div className="control-grid">
        <button type="button">
          <Pause aria-hidden="true" size={17} />
          Pause
        </button>
        <button type="button">
          <Play aria-hidden="true" size={17} />
          Resume
        </button>
        <button type="button">
          <RotateCcw aria-hidden="true" size={17} />
          Return
        </button>
        <button type="button">
          <Radio aria-hidden="true" size={17} />
          Retry
        </button>
      </div>
    </Panel>
  );
}
