import { Cpu } from "lucide-react";
import { formatEnumLabel, serviceTone } from "../../constants/adminLabels";
import type { RobotStatus } from "../../types/admin";
import { Panel } from "../ui/Panel";
import { StatusBadge } from "../ui/StatusBadge";

interface RobotHealthPanelProps {
  robotStatus: RobotStatus;
}

export function RobotHealthPanel({ robotStatus }: RobotHealthPanelProps) {
  return (
    <Panel
      eyebrow="System health"
      title={robotStatus.name}
      action={<Cpu aria-hidden="true" size={20} strokeWidth={1.8} />}
    >
      <div className="health-list">
        {robotStatus.services.map((service) => (
          <div className="health-row" key={service.name}>
            <div>
              <strong>{service.name}</strong>
              <span>{service.detail}</span>
            </div>
            <StatusBadge label={formatEnumLabel(service.status)} tone={serviceTone[service.status]} />
          </div>
        ))}
      </div>
    </Panel>
  );
}
