import { useEffect, useState } from "react";
import { Wrench } from "lucide-react";
import { Panel } from "../ui/Panel";
import { getArmJoints } from "../../services/armJointService";
import type { ArmJoint } from "../../types/admin";

function formatJointName(name: string): string {
  return name
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

interface JointRowProps {
  joint: ArmJoint;
}

function JointRow({ joint }: JointRowProps) {
  const pct = ((joint.position + Math.PI) / (2 * Math.PI)) * 100;
  const left = Math.min(50, pct);
  const width = Math.abs(50 - pct);

  return (
    <div className="arm-joint-row">
      <div className="arm-joint-row__header">
        <span className="arm-joint-row__name">{formatJointName(joint.name)}</span>
        <span className="arm-joint-row__values">
          {joint.position.toFixed(2)} rad &nbsp;·&nbsp; {joint.effort.toFixed(1)} N·m
        </span>
      </div>
      <div className="arm-joint-bar-track">
        <div
          className="arm-joint-bar-fill"
          style={{ left: `${left}%`, width: `${width}%` }}
        />
      </div>
    </div>
  );
}

export function ArmStatusPanel() {
  const [joints, setJoints] = useState<ArmJoint[]>([]);

  useEffect(() => {
    let mounted = true;

    const fetch = () => {
      getArmJoints().then((data) => {
        if (mounted) setJoints(data);
      });
    };

    fetch();
    const id = setInterval(fetch, 2000);

    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  return (
    <Panel
      eyebrow="Arm control"
      title="Joint states"
      action={<Wrench size={16} strokeWidth={1.75} color="var(--ink-muted)" />}
    >
      <div className="arm-joint-list">
        {joints.map((joint) => (
          <JointRow key={joint.name} joint={joint} />
        ))}
      </div>
    </Panel>
  );
}
